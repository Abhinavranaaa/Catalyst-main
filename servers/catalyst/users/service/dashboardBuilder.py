from django.utils import timezone
from datetime import timedelta

class DashboardBuilder:

    def build(self, stats, daily_rows):

        total_attempted = stats.total_attempted
        total_correct = stats.easy_correct+stats.medium_correct+stats.hard_correct

        accuracy = (
            total_correct / total_attempted
            if total_attempted else 0
        )

        avg_time = (
            stats.total_time_spent_seconds / total_attempted
            if total_attempted else 0
        )

        heatmap = self._build_heatmap(daily_rows)

        return {
            "current_streak": stats.current_streak,
            "max_streak": stats.max_streak,
            "accuracy_pct": round(accuracy * 100, 2),
            "avg_time_seconds": round(avg_time, 2),
            "total_correct": total_correct,
            "difficulty_breakdown": {
                "easy": stats.easy_correct,
                "medium": stats.medium_correct,
                "hard": stats.hard_correct,
            },
            "heatmap": heatmap,
        }

    def last_n_days(self,n:int):
        today=timezone.now().date()
        return [today-timedelta(days=i) for i in reversed(range(n))]



    def _build_heatmap(self, rows):
        result = []
        row_map = {r.date: r.total_attempted for r in rows}

        for day in self.last_n_days(30):
            result.append({
                "date": day,
                "count": row_map.get(day, 0)
            })

        return result
    
    