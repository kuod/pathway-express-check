import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import expression, pathways, reports
from app.services import gene_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    gene_cache.load()
    yield


app = FastAPI(
    title="Pathway Express Check",
    description="Co-expression analysis of MSigDB pathways in GTEx and public datasets.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pathways.router, prefix="/api/pathways", tags=["pathways"])
app.include_router(expression.router, prefix="/api/expression", tags=["expression"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


@app.get("/health")
def health():
    return {"status": "ok"}
