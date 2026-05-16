from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.middleware.request_id import RequestIdMiddleware
from app.telemetry.subscribers import register_subscribers
from app.workers.scheduler import start_scheduler, stop_scheduler

app = FastAPI(title='Proxmox Lab Manager')
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(router)
# Transitional versioned mount for forward compatibility
app.include_router(router, prefix='/v1')


@app.on_event('startup')
def _startup():
    register_subscribers()
    start_scheduler()


@app.on_event('shutdown')
def _shutdown():
    stop_scheduler()
