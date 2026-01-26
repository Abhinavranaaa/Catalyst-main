from dataclasses import dataclass
from collections import defaultdict
from dataclasses import dataclass
from collections import defaultdict
from typing import List

@dataclass
class StatsContext:
    submitted_attempts: List
    all_attempts: List
    question_lookup: dict

    def __post_init__(self):
        self.attempts_by_question = defaultdict(list)
        for attempt in self.all_attempts:
            self.attempts_by_question[attempt.question_id].append(attempt)


