import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question", "0002_question_subject"),
    ]

    operations = [
        migrations.CreateModel(
            name="QuestionAttachment",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "attachment_type",
                    models.CharField(
                        choices=[
                            ("image", "Image"),
                            ("code", "Code File"),
                            ("pdf", "PDF"),
                            ("text", "Plain Text / Markdown"),
                            ("audio", "Audio"),
                            ("video", "Video"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to="question_attachments/%Y/%m/",
                    ),
                ),
                ("inline_content", models.TextField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("order", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="question.question",
                    ),
                ),
            ],
            options={
                "verbose_name": "Question Attachment",
                "verbose_name_plural": "Question Attachments",
                "db_table": "question_attachments",
                "ordering": ["order", "created_at"],
            },
        ),
    ]
