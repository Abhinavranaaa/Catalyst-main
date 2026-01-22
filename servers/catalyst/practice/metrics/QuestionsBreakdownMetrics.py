from ..metrics.StatsMetrics import StatsMetrics
from ..StatsContext import StatsContext
from catalyst.constants import LAST_N_ATTEMPTS

class QuestionBreakdownMetric(StatsMetrics):

    def compute(self, ctx: StatsContext) -> dict:
        results = []

        for a in ctx.submitted_attempts:
            q = ctx.question_lookup.get(a.question_id)
            if not q:
                continue

            last_attempts = ctx.attempts_by_question[a.question_id][0:LAST_N_ATTEMPTS]

            results.append({
                "question_id": a.question_id,
                "selected_index": a.selected_index,
                "correct_index": q.correct_index,
                "last_attempts": [
                    {
                        "selected_index": la.selected_index,
                        "is_correct": la.is_correct,
                        "answered_at": la.answered_at,
                    }
                    for la in last_attempts
                ]
            })

        return {"questions": results}
    
