from abc import ABC, abstractmethod
from app.schemas import ProspectInput

class ProspectProvider(ABC):
    name = "base"

    @abstractmethod
    async def discover(self, website_domain: str, category: str,
                       keywords: list[str], country: str,
                       target_count: int = 100, **kwargs) -> list[ProspectInput]:
        raise NotImplementedError
