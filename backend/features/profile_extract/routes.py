from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.core.security import get_current_user
from backend.infra.database import log_activity

from .schema import ConsultantProfile
from .service import DEPLOYMENT, call_azure, image_block, pdf_to_text

router = APIRouter(tags=["profile-extract"])


@router.post("/extract", response_model=ConsultantProfile)
async def extract_profile(
    text:         Optional[str]              = Form(None),
    images:       Optional[List[UploadFile]] = File(None),
    current_user: dict                       = Depends(get_current_user),
):
    if not text and not images:
        raise HTTPException(status_code=422, detail="Provide at least one of 'text' or 'images'.")

    content: list = []
    image_count   = 0

    if text:
        content.append({"type": "text", "text": f"Extract consultant profile from:\n\n{text}"})
    if images:
        if not text:
            content.append({"type": "text", "text": "Extract consultant profile from the following file(s):"})
        for upload in images:
            raw = await upload.read()
            ct  = upload.content_type or ""
            if "pdf" in ct:
                extracted = pdf_to_text(raw)
                if not extracted:
                    raise HTTPException(status_code=422, detail=f"Could not extract text from PDF: {upload.filename}")
                content.append({"type": "text", "text": f"Resume (extracted from PDF '{upload.filename}'):\n\n{extracted}"})
            else:
                content.append(image_block(raw, ct or "image/jpeg"))
                image_count += 1

    action = "image" if image_count else "text"
    try:
        result = call_azure(content)
    except Exception as e:
        log_activity(current_user["user_id"], current_user["email"], action, image_count, "error", {"error": str(e)})
        raise

    log_activity(
        current_user["user_id"], current_user["email"],
        action, image_count, "success",
        {"name": result.name, "company": result.current_company},
    )
    return result


@router.post("/extract/batch", response_model=List[ConsultantProfile])
async def extract_profiles_batch(
    images:       List[UploadFile] = File(...),
    current_user: dict             = Depends(get_current_user),
):
    profiles: List[ConsultantProfile] = []
    for img in images:
        img_bytes = await img.read()
        content   = [
            {"type": "text", "text": "Extract consultant profile from this image:"},
            image_block(img_bytes, img.content_type or "image/jpeg"),
        ]
        result = call_azure(content)
        log_activity(current_user["user_id"], current_user["email"], "image", 1, "success",
                     {"name": result.name})
        profiles.append(result)
    return profiles


@router.get("/health")
def health():
    return {"status": "ok", "app": "SourceAssist", "model": DEPLOYMENT}
