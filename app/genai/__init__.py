from app.config import settings
from app.genai.gemini import explain_prospect_gemini
from app.genai.ollama import explain_prospect as explain_prospect_ollama

async def explain_prospect(domain: str, category: str, evidence: dict) -> str:
    """
    Unified GenAI dispatcher: delegates to Google Gemini if configured,
    or local Ollama if configured, otherwise returns status.
    """
    if settings.enable_gemini_explanations and settings.gemini_api_key:
        return await explain_prospect_gemini(domain, category, evidence)
    elif settings.enable_ollama_explanations:
        return await explain_prospect_ollama(domain, category, evidence)
    return "GenAI explanations are disabled. Enable either GEMINI or OLLAMA in settings."
