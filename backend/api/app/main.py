from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.claim_worker import ClaimWorker
from app.db import close_pool, ensure_mqtt_service_credentials, open_pool
from app.device_message_worker import DeviceMessageWorker
from app.routes import claims, devices, health, sessions, tenants


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    ensure_mqtt_service_credentials()
    claim_worker = ClaimWorker()
    device_message_worker = DeviceMessageWorker()
    claim_worker.start()
    device_message_worker.start()
    yield
    device_message_worker.stop()
    claim_worker.stop()
    close_pool()


app = FastAPI(title="AI Connect Controller", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(claims.router, prefix="/v1", tags=["claims"])
app.include_router(devices.router, prefix="/v1", tags=["devices"])
app.include_router(sessions.router, prefix="/v1", tags=["sessions"])
app.include_router(tenants.router, prefix="/v1", tags=["tenants"])
