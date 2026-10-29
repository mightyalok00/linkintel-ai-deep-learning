import httpx
from app.config import settings

def generate_fallback_pitch(domain: str, category: str, evidence: dict) -> str:
    status = str(evidence.get("cost_status", "pending_verification")).replace("_", " ").title()
    relevance = evidence.get("relevance", "Evaluated")
    authority = evidence.get("authority", "Evaluated")
    return (
        f"### 1. Opportunity Assessment: {domain}\n"
        f"- **Niche Relevance**: Directly targeted at the '{category}' sector.\n"
        f"- **Cost Status**: {status}.\n"
        f"- **Key Metrics**: Relevance: {relevance} | Authority: {authority}\n\n"
        f"### 2. Risk & Uncertainty Analysis\n"
        f"- Editorial review required: Verify that submission criteria remain zero-cost.\n"
        f"- Confirm dofollow link attribution and indexability upon acceptance.\n\n"
        f"### 3. Personalized Outreach Pitch\n\n"
        f"Subject: Resource recommendation for your {category} directory ({domain})\n\n"
        f"Hi Editor at {domain},\n\n"
        f"I was reviewing your excellent resources section on {domain} and appreciated your curated coverage in the {category} space.\n\n"
        f"We have built a dedicated, zero-cost resource and guide that provides direct value to professionals in this area. I believe it would be a valuable addition for your readers looking for actionable solutions.\n\n"
        f"Would you be open to reviewing it for a potential listing on your page?\n\n"
        f"Best regards,\n"
        f"[Your Name]\n"
        f"[Your Title & Website]"
    )

async def explain_prospect_gemini(domain: str, category: str, evidence: dict) -> str:
    """
    Generates evidence-grounded prospect viability assessment and ethical outreach pitch
    using Google Gemini API with automatic fallback on temporary server spikes.
    """
    if not settings.gemini_api_key:
        return generate_fallback_pitch(domain, category, evidence)

    prompt = (
        "You are an expert, ethical SEO backlink intelligence analyst.\n"
        "Analyze the following opportunity using strictly the provided facts. "
        "Do not invent DA/DR numbers, traffic statistics, or promise link placement.\n\n"
        f"Target Domain: {domain}\n"
        f"Category: {category}\n"
        f"Verified Data & Evidence: {evidence}\n\n"
        "Provide a concise 3-part breakdown:\n"
        "1. Opportunity Assessment: Viability based on verified metrics and cost status.\n"
        "2. Risk/Uncertainty Warning: Any missing metrics or terms requiring caution.\n"
        "3. Personalized Outreach Pitch: A courteous, value-first pitch to the site editor."
    )

    models_to_try = [
        (settings.gemini_model or "gemini-flash-latest").replace("models/", ""),
        "gemini-flash-latest",
        "gemini-3.8-flash",
    ]

    async with httpx.AsyncClient(timeout=15) as client:
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.gemini_api_key}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and parts[0].get("text"):
                            return parts[0]["text"]
                elif response.status_code in {503, 429}:
                    continue
            except (httpx.HTTPError, ValueError):
                continue

    # Fallback to local pitch generation if Gemini servers are temporarily undergoing high-load spikes
    return generate_fallback_pitch(domain, category, evidence)
