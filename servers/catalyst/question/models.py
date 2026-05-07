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


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    topic = models.CharField(max_length=255, blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    difficulty = models.CharField(max_length=50, blank=True, null=True)
    source = models.TextField(blank=True, null=True)
    options = ArrayField(models.TextField(), blank=False, null=False)
    correct_index = models.IntegerField()
    text = models.TextField()
    explanation = models.TextField(blank=True, null=True)

    # Enrichment state machine
    enrichment_status = models.CharField(
        max_length=30,
        choices=EnrichmentStatus.choices,
        default=EnrichmentStatus.RAW,
    )
    enrichment_attempts = models.PositiveIntegerField(default=0)
    enrichment_error = models.TextField(blank=True, null=True)
    enriched_at = models.DateTimeField(blank=True, null=True)

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







