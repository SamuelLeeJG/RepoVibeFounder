"""Alpha-Beta Decision Intelligence Terminal — FastAPI entry point (v2.0)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.auth.routes import auth_router
from backend.db.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB tables. Shutdown: close DB pool."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Alpha-Beta Decision Intelligence Terminal",
    version="2.0.0",
    description="Technical signal engine with contextual thesis generation, auth, and portfolio optimization.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
