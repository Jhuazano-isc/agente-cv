import logging
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CV_TOOL_SCHEMA = {
    "type": "function",
    "name": "read_cv",
    "description": "Lee el contenido completo del CV de Jesus Huazano. Usala SIEMPRE antes de responder cualquier pregunta sobre su experiencia, proyectos, habilidades o cualquier dato necesario.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

FETCH_LINK_TOOL_SCHEMA = {
    "type": "function",
    "name": "fetch_link",
    "description": (
        "Consulta el perfil de LinkedIn o el portafolio de GitHub mencionados en el CV. "
        "SOLO soporta esos dos dominios (linkedin.com, github.com) si la plataforma lo permite, en caso contrario mencionar esa limitante. " 
        "Para cualquier otro enlace, NO la uses — respondé directamente que no tenés la habilidad de consultarlo."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "La URL exacta del perfil de LinkedIn o GitHub, tal como aparece en el CV."
            }
        },
        "required": ["url"]
    }
}

def read_cv() -> str:
    cv_path = Path(__file__).parent / "sources" / "CV-Huazano-FULL-EN_V1.md"
    return cv_path.read_text(encoding="utf-8")

async def fetch_link(url: str) -> str:
    if "linkedin.com" in url:
        return await _fetch_linkedin(url)
    if "github.com" in url:
        return await _fetch_github(url)

    logger.warning("Blocked fetch_link call for disallowed domain: %s", url)

    # Guardrail: para limitar el uso de dominios extra
    return (
        "No tengo la habilidad de consultar ese enlace. "
        "Solo puedo revisar el perfil de LinkedIn y el portafolio de GitHub, si el enlace lo permite."
    )

async def _fetch_linkedin(url: str) -> str:
    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; CVAgentBot/1.0)"},
        ) as client:
            resp = await client.get(url)
    except httpx.RequestError:
        return "No pude conectarme a LinkedIn en este momento. Puedo responder con lo que ya sé por el CV."

    if resp.status_code != 200 or "authwall" in str(resp.url):
        return "LinkedIn requiere iniciar sesión para ver el perfil, así que no puedo consultarlo en vivo. Puedo responder con lo que ya sé por el CV."

    soup = BeautifulSoup(resp.text, "html.parser")
    og_title = soup.find("meta", property="og:title")
    og_description = soup.find("meta", property="og:description")

    if not og_title and not og_description:
        return "LinkedIn no expuso información pública en este momento. Puedo responder con lo que ya sé por el CV."

    items = [tag.get("content", "") for tag in (og_title, og_description) if tag is not None]
    return " — ".join(items)


async def _fetch_github(url: str) -> str:
    username = url.rstrip("/").split("/")[-1]
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"sort": "updated", "per_page": 10},
        )
        resp.raise_for_status()
        repos = resp.json()
    return "\n".join(
        f"- {r['name']}: {r['description'] or 'sin descripción'} ({r['html_url']})"
        for r in repos
    )