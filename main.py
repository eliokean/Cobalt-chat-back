"""
Point d'entrée principal FastAPI
Assemble les middlewares transverses et monte les routeurs de chaque module DDD.
"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import settings
from src.core.database import init_db
from src.core.realtime import manager
from src.modules.auth.presentation.routes import router as auth_router
from src.modules.chat.presentation.routes import router as chat_router
from src.modules.chat.presentation.routes import ws_router
from src.modules.crypt.presentation.routes import router as crypt_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    manager.bind_loop(asyncio.get_running_loop())
    yield


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Middlewares transverses (CORS)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Inclusion modulaire des Bounded Contexts
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(crypt_router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/api/v1")

    # 3. Routes racine & healthcheck
    @app.get("/", tags=["Health"])
    def read_root():
        return {
            "status": "online",
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
        }

    @app.get("/health", tags=["Health"])
    def health_check():
        return {"status": "ok"}

    return app


app = create_application()
