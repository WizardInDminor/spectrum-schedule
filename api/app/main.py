from fastapi import FastAPI

from app.routers import (
    activities,
    auth,
    children,
    events,
    preferences,
    schedules,
    templates,
    users,
)

app = FastAPI(title="Spectrum Schedule API", version="0.1.0")

for router in (
    auth.router,
    users.router,
    children.router,
    templates.router,
    schedules.router,
    events.router,
    preferences.router,
    activities.router,
):
    app.include_router(router, prefix="/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}
