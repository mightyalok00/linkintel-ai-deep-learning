from urllib.parse import urlparse
from app.config import settings
from app.providers.demo import DemoProvider
from app.providers.live_search import LiveSearchProvider
from app.scoring import score_prospect
from app.deep_learning.relevance import batch_semantic_similarity
from app.ml.features import FEATURE_COLUMNS
from app.ml.spam_model import predict_spam_risk

PROVIDERS = {
    "demo": DemoProvider(),
    "live_search": LiveSearchProvider()
}

async def analyze(request, scan_id: str, progress_callback=None):
    website_domain = urlparse(str(request.website_url)).hostname or ""
    if progress_callback:
        await progress_callback("Validating request scope and provider selection...", 5, 0)

    if request.prospects is not None:
        prospects, provider_name = request.prospects, "user_supplied"
        warnings = ["User-supplied rows are not independently verified."]
    elif request.provider.lower() in PROVIDERS:
        target_count = getattr(request, "target_count", 100)
        provider = PROVIDERS[request.provider.lower()]
        try:
            prospects = await provider.discover(
                website_domain, request.category, request.keywords, request.country,
                target_count=target_count, progress_callback=progress_callback
            )
        except TypeError:
            prospects = await provider.discover(
                website_domain, request.category, request.keywords, request.country,
                target_count=target_count
            )
        provider_name = request.provider.lower()
        if provider_name == "demo":
            warnings = ["Demo records are synthetic, not live backlink opportunities."]
        else:
            warnings = ["Live web discovery: verify editorial guidelines and terms before submission."]
    else:
        raise ValueError(f"Provider '{request.provider}' is not configured.")

    unique: dict[str, any] = {}
    for prospect in prospects:
        unique.setdefault(prospect.domain, prospect)

    prospect_list = list(unique.values())
    query = " ".join([request.category, *request.keywords])

    # Vectorized Deep Learning semantic relevance batch
    similarities: list[float | None] = [None] * len(prospect_list)
    if request.use_deep_learning and settings.enable_deep_learning:
        if progress_callback:
            await progress_callback("Vectorizing candidate text and computing semantic similarity...", 78, len(prospect_list))
        candidate_texts = [
            " ".join([p.title, p.description, p.category])
            for p in prospect_list
        ]
        similarities = batch_semantic_similarity(query, candidate_texts, settings.semantic_model)
        if any(s is None for s in similarities):
            warnings.append("Semantic model unavailable or produced null for one or more prospects.")
    elif request.use_deep_learning:
        warnings.append("Deep learning requested but ENABLE_DEEP_LEARNING is false.")

    if progress_callback:
        await progress_callback("Evaluating spam risk, authority metrics, and zero-cost policy...", 88, len(prospect_list))

    results = []
    for prospect, similarity in zip(prospect_list, similarities):
        predicted_risk = None
        # Predict spam risk from tabular features if enabled and risk metric is not already given
        if settings.enable_spam_model and prospect.spam_risk is None:
            feature_dict = {
                col: getattr(prospect, col, None)
                for col in FEATURE_COLUMNS
            }
            if all(v is not None for v in feature_dict.values()):
                predicted_risk = predict_spam_risk(feature_dict)

        results.append(score_prospect(prospect, similarity, predicted_risk))

    results.sort(key=lambda item: (
        item.cost_status.value == "verified_free",
        item.score.opportunity_score is not None,
        item.score.opportunity_score or -1), reverse=True)

    if progress_callback:
        await progress_callback("Scan completed and ranked successfully.", 100, len(results))

    return {
        "scan_id": scan_id,
        "website_domain": website_domain,
        "category": request.category,
        "provider": provider_name,
        "prospects_found": len(results),
        "verified_free_count": sum(x.cost_status.value == "verified_free" for x in results),
        "pending_verification_count": sum(
            x.cost_status.value == "pending_verification" for x in results),
        "prospects": [x.model_dump(mode="json") for x in results],
        "warnings": sorted(set(warnings)),
    }
