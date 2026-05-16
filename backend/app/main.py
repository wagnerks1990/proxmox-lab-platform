from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.middleware import request_id_middleware

app = FastAPI(title='Proxmox Lab Manager')
app.middleware('http')(request_id_middleware)
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
