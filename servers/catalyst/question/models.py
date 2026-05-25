import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils import timezone


class EnrichmentStatus(models.TextChoices):
    RAW = "raw", "Raw"
    PENDING_ENRICHMENT = "pending_enrichment", "Pending Enrichment"
    ENRICHING = "enriching", "Enriching"
    ENRICHED = "enriched", "Enriched"
    FAILED = "failed", "Failed"


# Allowed transitions: maps each state to the set of states it may move to.
_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    EnrichmentStatus.RAW: {EnrichmentStatus.PENDING_ENRICHMENT},
    EnrichmentStatus.PENDING_ENRICHMENT: {EnrichmentStatus.ENRICHING, EnrichmentStatus.RAW},
    EnrichmentStatus.ENRICHING: {EnrichmentStatus.ENRICHED, EnrichmentStatus.FAILED},
    EnrichmentStatus.ENRICHED: set(),
    EnrichmentStatus.FAILED: {EnrichmentStatus.PENDING_ENRICHMENT},
}

# Maps integer difficulty (1-5) back to the legacy string labels that the
# rest of the codebase and API surface use.  Values 2 and 4 are reserved for
# IRT-derived granularity; they fold into the nearest canonical label so
# existing string comparisons ("easy"/"medium"/"hard") keep working.
_DIFFICULTY_LABEL: dict[int, str] = {
    1: "easy",
    2: "easy",
    3: "medium",
    4: "hard",
    5: "hard",
}


class DifficultySource(models.TextChoices):
    MANUAL = "manual", "Manual"
    IRT = "irt", "IRT"
    LLM_ESTIMATED = "llm_estimated", "LLM Estimated"


class BloomLevelSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    LLM_CLASSIFIED = "llm_classified", "LLM Classified"


class ExplanationSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    LLM_GENERATED = "llm_generated", "LLM Generated"


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    # Integer 1–5 (1=easiest, 5=hardest). Use .difficulty_label for the
    # legacy "easy"/"medium"/"hard" string wherever the API or analytics need it.
    difficulty = models.PositiveSmallIntegerField(blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    options = ArrayField(models.TextField(), blank=False, null=False)
    correct_index = models.IntegerField()
    text = models.TextField()
    explanation = models.TextField(blank=True, null=True)
    distractor_explanations = models.TextField(blank=True, null=True)

    # Code snippet fields — populated for snippet-based questions.
    # snippet_language: GeSHi/highlighter language identifier, e.g. "java", "python", "cpp", "sql".
    # snippet_body: the raw source code to display.
    # snippet_line_range: optional [start, end] 1-indexed line numbers to highlight; null = show all.
    snippet_language = models.CharField(max_length=50, blank=True, null=True)
    snippet_body = models.TextField(blank=True, null=True)
    snippet_line_range = ArrayField(models.PositiveSmallIntegerField(), size=2, blank=True, null=True)

    # Bloom's Taxonomy level 1–6 (Remember → Create).
    bloom_level = models.PositiveSmallIntegerField(blank=True, null=True)

    # Provenance — who/what set each enriched value.
    difficulty_source = models.CharField(
        max_length=20,
        choices=DifficultySource.choices,
        blank=True,
        null=True,
    )
    bloom_level_source = models.CharField(
        max_length=20,
        choices=BloomLevelSource.choices,
        blank=True,
        null=True,
    )
    explanation_source = models.CharField(
        max_length=20,
        choices=ExplanationSource.choices,
        blank=True,
        null=True,
    )

    # Enrichment state machine
    enrichment_status = models.CharField(
        max_length=30,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.RAW,
    )
    enrichment_attempts = models.PositiveIntegerField(default=0)
    enrichment_error = models.TextField(blank=True, null=True)
    enriched_at = models.DateTimeField(blank=True, null=True)

    @property
    def difficulty_label(self):
        """
        Returns the legacy string label ("easy" / "medium" / "hard") for the
        integer difficulty value so all existing API responses and analytics
        code continue to work without modification.

        Returns None when difficulty is unset — callers that need a fallback
        should use ``question.difficulty_label or "medium"``.
        """
        if self.difficulty is None:
            return None
        return _DIFFICULTY_LABEL.get(self.difficulty)

    def transition_status(self, new_status: str) -> None:
        """
        Move this question to new_status, persisting enrichment_status (and
        enriched_at when transitioning to ENRICHED) via save().

        Raises ValueError for illegal transitions so callers never silently
        leave the state machine in an inconsistent state.
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.enrichment_status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Illegal enrichment transition: {self.enrichment_status!r} → {new_status!r}. "
                f"Allowed: {sorted(allowed) or 'none'}"
            )

        update_fields = ["enrichment_status"]
        self.enrichment_status = new_status

        if new_status == EnrichmentStatus.ENRICHED:
            self.enriched_at = timezone.now()
            update_fields.append("enriched_at")

        self.save(update_fields=update_fields)

    def __str__(self):
        return self.text[:80]

    class Meta:
        db_table = 'questions'
        verbose_name = "Question"
        verbose_name_plural = "Questions"