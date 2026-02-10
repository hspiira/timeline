# Vercel FastAPI zero-config entrypoint (app/index.py is a detected path).
# See https://vercel.com/docs/frameworks/backend/fastapi
from app.main import app

__all__ = ["app"]
