import uuid
from django.core.management.base import BaseCommand
from datasets import load_dataset, get_dataset_config_names
from question.models import Question  # Update if your app is named differently


class Command(BaseCommand):
    help = "Import MMLU questions into the Question model"

    def handle(self, *args, **options):
        subject_names = get_dataset_config_names("cais/mmlu")

        # ✅ Skip the "all" config which is not a real subject
        subject_names = [name for name in subject_names if name != "all"]

        total_inserted = 0

        for subject in subject_names:
            self.stdout.write(self.style.NOTICE(f"Loading subject: {subject}"))

            try:
                ds = load_dataset("cais/mmlu", subject)
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to load {subject}: {e}"))
                continue

            for split in ["train", "validation", "test"]:
                if split not in ds:
                    continue

                for record in ds[split]:
                    try:
                        Question.objects.create(
                            id=uuid.uuid4(),
                            topic=None,
                            subject=subject,
                            difficulty=None,
                            source="MMLU",
                            options=record["choices"],
                            correct_index=record["answer"],
                            text=record["question"],
                        )
                        total_inserted += 1
                    except Exception as e:
                        self.stderr.write(f"Error inserting record: {e}")
                        continue

        self.stdout.write(self.style.SUCCESS(f"✅ Imported {total_inserted} questions from MMLU."))
