from app.schemas import CostStatus, ProspectInput, ProspectResult, ScoreBreakdown

WEIGHTS = {"relevance": 0.30, "authority": 0.20,
           "backlink_quality": 0.20, "spam_safety": 0.20,
           "editorial_potential": 0.10}

def cost_status(p: ProspectInput) -> CostStatus:
    if (p.placement_fee is not None and p.submission_fee is not None
        and p.placement_fee == 0 and p.submission_fee == 0
        and p.mandatory_purchase is False and p.paid_plan_required is False
        and p.free_submission_available and p.terms_verified):
        return CostStatus.VERIFIED_FREE
    if ((p.placement_fee is not None and p.placement_fee > 0)
        or (p.submission_fee is not None and p.submission_fee > 0)
        or p.mandatory_purchase is True or p.paid_plan_required is True):
        return CostStatus.PAID
    return CostStatus.PENDING

def score_prospect(p: ProspectInput, semantic_similarity: float | None = None,
                   predicted_spam_risk: float | None = None) -> ProspectResult:
    missing = [name for name in ("relevance", "authority_score",
               "backlink_quality", "spam_risk") if getattr(p, name) is None]
    risk = p.spam_risk if p.spam_risk is not None else predicted_spam_risk
    if p.spam_risk is None and predicted_spam_risk is not None:
        missing = [field for field in missing if field != "spam_risk"]
    editorial = min(100.0, 50.0 + (15 if p.evidence_url and p.terms_verified else 0)
                    + (10 if p.free_submission_available else 0))
    relevance = p.relevance
    if semantic_similarity is not None:
        semantic_score = max(0.0, min(100.0, semantic_similarity * 100.0))
        relevance = semantic_score if relevance is None else (0.5 * relevance + 0.5 * semantic_score)
        missing = [field for field in missing if field != "relevance"]
    score = None
    confidence = "low"
    if not missing and risk is not None and relevance is not None:
        score = (0.30 * relevance + 0.20 * p.authority_score
                 + 0.20 * p.backlink_quality + 0.20 * (100 - risk)
                 + 0.10 * editorial)
        confidence = "medium" if p.terms_verified else "low"
    reasons = []
    status = cost_status(p)
    if status == CostStatus.VERIFIED_FREE:
        reasons.append("Cost fields and submission terms are explicitly marked verified.")
    elif status == CostStatus.PENDING:
        reasons.append("Cost eligibility is unverified; do not treat this as free.")
    else:
        reasons.append("A fee, mandatory purchase, or paid plan was identified.")
    if missing:
        reasons.append("Ranking withheld; missing metrics: " + ", ".join(missing))
    if semantic_similarity is not None:
        reasons.append("Semantic similarity is a relevance signal, not a link-acquisition probability.")
    if predicted_spam_risk is not None and p.spam_risk is None:
        reasons.append("Spam risk comes from the configured ML model; validate calibration on real labels.")
    return ProspectResult(
        domain=p.domain, page_url=p.page_url, title=p.title, description=p.description,
        cost_status=status,
        score=ScoreBreakdown(
            relevance=relevance, authority=p.authority_score,
            backlink_quality=p.backlink_quality, spam_risk=risk,
            editorial_potential=editorial,
            opportunity_score=round(score, 2) if score is not None else None,
            confidence=confidence, missing_fields=missing,
            semantic_similarity=semantic_similarity),
        evidence_url=p.evidence_url, link_type=p.link_type, reasons=reasons)
