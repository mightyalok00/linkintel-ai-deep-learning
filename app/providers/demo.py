from app.providers.base import ProspectProvider
from app.schemas import ProspectInput

class DemoProvider(ProspectProvider):
    name = "demo"

    async def discover(self, website_domain: str, category: str,
                       keywords: list[str], country: str,
                       target_count: int = 100, **kwargs) -> list[ProspectInput]:
        # Synthetic test rows, not live opportunities or metrics.
        return [
            ProspectInput(domain="example.org", page_url="https://example.org/resources",
                title=f"Example {category} resources (DEMO)",
                description="Synthetic demo row; replace with verified source data.",
                category=category, authority_score=72, backlink_quality=68, spam_risk=8,
                relevance=84, placement_fee=0, submission_fee=0,
                mandatory_purchase=False, paid_plan_required=False,
                free_submission_available=True, terms_verified=True,
                evidence_url="https://example.org/resources", link_type="unknown"),
            ProspectInput(domain="sample.net", page_url="https://sample.net/submit",
                title=f"Sample {category} submission page (DEMO)",
                description="Synthetic row; cost terms are unknown.",
                category=category, relevance=62, evidence_url="https://sample.net/submit")
        ]
