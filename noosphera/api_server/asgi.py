from .main import create_app

# ASGI entrypoint for uvicorn/gunicorn
app = create_app()
