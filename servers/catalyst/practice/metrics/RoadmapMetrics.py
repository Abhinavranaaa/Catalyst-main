from ..metrics.StatsMetrics import StatsMetrics
from ..StatsContext import StatsContext

class RoadmapCompletionMetric(StatsMetrics):

    def compute(self, ctx: StatsContext) -> dict:
        solved_once = {
            a.question_id
            for a in ctx.all_attempts
            if a.is_correct
        }

        total = len(ctx.question_lookup)

        return {
            "roadmap_completion_pct": round(
                (len(solved_once) / total) * 100, 2
            ) if total else 0.0
        }

