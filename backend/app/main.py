from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.folders import router as folders_router
from app.api.routes.health import router as health_router
from app.api.routes.notes import router as notes_router
from app.api.routes.search import router as search_router
from app.api.routes.users import router as users_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth_router)
    app.include_router(folders_router)
    app.include_router(health_router)
    app.include_router(notes_router)
    app.include_router(search_router)
    app.include_router(users_router)

    return app


app = create_app()
