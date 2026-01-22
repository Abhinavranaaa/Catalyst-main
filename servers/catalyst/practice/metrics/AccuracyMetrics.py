from ..metrics.StatsMetrics import StatsMetrics
from ..StatsContext import StatsContext

class AccuracyMetric(StatsMetrics):

    def compute(self, ctx: StatsContext) -> dict:
        attempts = ctx.submitted_attempts
        if not attempts:
            return {"accuracy_pct": 0.0}

        correct = sum(1 for a in attempts if a.is_correct)
        return {
            "accuracy_pct": round((correct / len(attempts)) * 100, 2)
        }
