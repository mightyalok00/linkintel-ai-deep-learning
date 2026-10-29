from app.schemas import ProspectInput, CostStatus
from app.scoring import cost_status, score_prospect

def test_unknown_cost_is_not_free():
    assert cost_status(ProspectInput(domain="example.com")) == CostStatus.PENDING

def test_paid_placement_is_rejected():
    p = ProspectInput(domain="example.com", placement_fee=100, submission_fee=0,
        mandatory_purchase=False, paid_plan_required=False,
        free_submission_available=True, terms_verified=True)
    assert cost_status(p) == CostStatus.PAID

def test_verified_free_requires_all_fields():
    p = ProspectInput(domain="example.com", placement_fee=0, submission_fee=0,
        mandatory_purchase=False, paid_plan_required=False,
        free_submission_available=True, terms_verified=True)
    assert cost_status(p) == CostStatus.VERIFIED_FREE

def test_missing_metrics_withhold_score():
    result = score_prospect(ProspectInput(domain="example.com"))
    assert result.score.opportunity_score is None
    assert result.score.missing_fields

def test_full_scoring_calculation():
    p = ProspectInput(
        domain="example.com",
        authority_score=80.0,
        backlink_quality=75.0,
        spam_risk=10.0,
        relevance=90.0,
        placement_fee=0,
        submission_fee=0,
        mandatory_purchase=False,
        paid_plan_required=False,
        free_submission_available=True,
        terms_verified=True,
        evidence_url="https://example.com/terms"
    )
    res = score_prospect(p)
    assert res.cost_status == CostStatus.VERIFIED_FREE
    assert res.score.opportunity_score is not None
    assert res.score.confidence == "medium"
    assert len(res.score.missing_fields) == 0

def test_semantic_similarity_integration():
    p = ProspectInput(
        domain="example.com",
        authority_score=80.0,
        backlink_quality=70.0,
        spam_risk=15.0,
        placement_fee=0,
        submission_fee=0,
        mandatory_purchase=False,
        paid_plan_required=False,
        free_submission_available=True,
        terms_verified=True
    )
    # relevance is None on prospect, but semantic similarity is provided
    res = score_prospect(p, semantic_similarity=0.85)
    assert res.score.relevance == 85.0
    assert res.score.opportunity_score is not None

def test_spam_model_prediction():
    from app.ml.spam_model import predict_spam_risk
    # Legitimate features
    legit_features = {
        "referring_domains": 1200.0,
        "outbound_link_ratio": 0.05,
        "content_relevance": 0.88,
        "domain_age_years": 8.5,
        "anchor_diversity": 0.85,
        "thin_content_ratio": 0.05
    }
    risk_legit = predict_spam_risk(legit_features)
    assert risk_legit is not None
    assert risk_legit < 35.0

    # Spam features
    spam_features = {
        "referring_domains": 10.0,
        "outbound_link_ratio": 0.75,
        "content_relevance": 0.10,
        "domain_age_years": 0.4,
        "anchor_diversity": 0.12,
        "thin_content_ratio": 0.85
    }
    risk_spam = predict_spam_risk(spam_features)
    assert risk_spam is not None
    assert risk_spam > 65.0

