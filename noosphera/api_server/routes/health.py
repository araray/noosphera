from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health", summary="Liveness/health probe (public)")
async def health() -> dict[str, str]:
    # Keep payload minimal to satisfy smoke test and remain stable across steps.
    return {"status": "ok", "service": "noosphera"}
