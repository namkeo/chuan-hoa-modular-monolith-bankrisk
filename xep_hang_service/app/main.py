import logging
from contextlib import asynccontextmanager
# Updated for real DuLieuTinhDiem criteria scoring
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import connect_to_mongo, close_mongo_connection
from app.core.exceptions import BaseScoringException

from app.routers import (
    bo_tieu_chi,
    nhom_tieu_chi,
    chi_tieu,
    du_lieu_tinh_diem,
    doi_tuong,
    tinh_diem
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API phục vụ tính điểm và xếp hạng tổ chức tín dụng theo bộ tiêu chí",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom Exception Handler
@app.exception_handler(BaseScoringException)
async def custom_scoring_exception_handler(request: Request, exc: BaseScoringException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# Include Routers
app.include_router(bo_tieu_chi.router)
app.include_router(nhom_tieu_chi.router)
app.include_router(chi_tieu.router)
app.include_router(du_lieu_tinh_diem.router)
app.include_router(doi_tuong.router)
app.include_router(tinh_diem.router)

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "docs_url": "/docs"
    }
