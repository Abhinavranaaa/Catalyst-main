from ..metrics.StatsMetrics import StatsMetrics
from ..StatsContext import StatsContext

class FactoryEngine:

    def __init__(self,metrics: list[StatsMetrics]):
        self.metrics = metrics

    def run(self, ctx:StatsContext) -> dict:
        report={}
        for metric in self.metrics:
            report.update(metric.compute(ctx))

        return report
    

        