from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.features.auth.routes import router as auth_router
from backend.features.profile_extract.routes import router as extract_router
from backend.infra.database import init_db

app = FastAPI(title="SourceAssist", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(extract_router)


@app.on_event("startup")
def startup():
    init_db()
