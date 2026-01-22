from dataclasses import dataclass
from collections import defaultdict
from dataclasses import dataclass
from collections import defaultdict
from typing import List

@dataclass
class StatsContext:
    submitted_attempts: List
    all_attempts: List
    roadmap_questions: List

    def __post_init__(self):
        # Map Question UUID → Question object
        self.question_lookup = {
            rq.question.id: rq.question
            for rq in self.roadmap_questions
        }

        self.attempts_by_question = defaultdict(list)

        for attempt in self.all_attempts:
            self.attempts_by_question[attempt.question_id].append(attempt)


