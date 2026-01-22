from ..metrics.StatsMetrics import StatsMetrics
from ..StatsContext import StatsContext

class MeanTimeMetric(StatsMetrics):

    def compute(self, ctx: StatsContext) -> dict:
        times = [
            a.time_taken_seconds
            for a in ctx.submitted_attempts
            if a.time_taken_seconds is not None
        ]

        return {
            "mean_time_seconds": (
                sum(times) / len(times) if times else None
            )
        }
