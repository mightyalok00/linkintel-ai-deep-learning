import httpx

from app.config import settings


async def explain_prospect(domain: str, category: str, evidence: dict) -> str:
    if not settings.enable_ollama_explanations:
        return "GenAI explanations are disabled."
    prompt = ("Use only supplied facts. Do not invent authority or backlink metrics. "
              "Explain uncertainties and suggest ethical outreach. "
              f"domain={domain}; category={category}; evidence={evidence}")
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/generate",
                json={"model": settings.ollama_model, "prompt": prompt, "stream": False})
            response.raise_for_status()
            return response.json().get("response", "No explanation returned.")
    except (httpx.HTTPError, ValueError):
        return "GenAI unavailable; consult evidence and score breakdown."
