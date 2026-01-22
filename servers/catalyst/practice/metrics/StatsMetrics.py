from abc import ABC, abstractmethod
from ..StatsContext import StatsContext

class StatsMetrics(ABC):
    @abstractmethod
    def compute(self, ctx: StatsContext) -> dict:
        pass

