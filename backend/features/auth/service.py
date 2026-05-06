from fastapi import HTTPException

from backend.core.config import ALLOWED_DOMAINS


def check_domain(email: str):
    domain = email.split("@")[-1].lower()
    if domain not in ALLOWED_DOMAINS:
        raise HTTPException(
            status_code=403,
            detail="Only @joulestowatts.com or @joulestowatts.co emails are allowed",
        )
