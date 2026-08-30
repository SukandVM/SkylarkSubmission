from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.routers import chat, boards, health

app = FastAPI(
    title="Skylark Drones BI Agent",
    description="AI-powered business intelligence agent for Skylark Drones",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(boards.router)


@app.get("/")
async def root():
    return {
        "name": "Skylark Drones BI Agent",
        "version": "1.0.0",
        "docs": "/docs",
    }
