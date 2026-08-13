import logging
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi import FastAPI
from app.routers import responses
from app.memory import init_db

from dotenv import load_dotenv
import os
import gradio as gr
from chat_ui import demo as chat_demo

load_dotenv()

debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"
log_level = "DEBUG" if debug_mode else "INFO"
title = os.getenv("APP_TITLE", "Banorte CV Agent")

logging.basicConfig(
    level=log_level,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title=title)
init_db()
app.include_router(responses.router)
app = gr.mount_gradio_app(app, chat_demo, path="/chat")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/.well-known/agent-card.json")
def agent_card():
    return {
        "name": "Wazy — Agente de CV de Jesus Huazano",
        "description": (
            "Agente conversacional que representa la trayectoria profesional de Jesus Huazano. "
            "Responde preguntas sobre experiencia, proyectos y habilidades basándose en su CV real, "
            "con acceso en vivo a su portafolio de GitHub y su perfil de LinkedIn."
        ),
        "supportedInterfaces": [
            {
                "url": "https://agent-cv-wazy-25358.fly.dev/v1/responses",
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "1.0",
            }
        ],
        "provider": {
            "organization": "Jesus Huazano",
            "url": "https://github.com/Jhuazano-isc/agente-cv",
        },
        "version": "1.0.0",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "extendedAgentCard": False,
        },
        "skills": [
            {
                "id": "answer_cv_questions",
                "name": "Responder preguntas sobre el CV",
                "description": "Responde preguntas sobre la experiencia profesional, habilidades y proyectos de Jesus Huazano, basándose en su CV.",
                "tags": ["cv", "trayectoria profesional"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/plain"],
            },
            {
                "id": "fetch_live_profile_links",
                "name": "Consultar perfiles en vivo",
                "description": "Obtiene datos en vivo del portafolio de GitHub o el perfil de LinkedIn de Jesus Huazano cuando es relevante para la pregunta.",
                "tags": ["github", "linkedin"],
                "inputModes": ["text/plain"],
                "outputModes": ["text/plain"],
            },
        ],
        "securitySchemes": {
            "bearer_auth": {"type": "http", "scheme": "bearer"}
        },
        "security": [{"bearer_auth": []}],
    }

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = await request.body()
    logger.error(
        "422 en %s | errores=%s | body=%s",
        request.url.path,
        exc.errors(),
        body.decode("utf-8", errors="replace"),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})