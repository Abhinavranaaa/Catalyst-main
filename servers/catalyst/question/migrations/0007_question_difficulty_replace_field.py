from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Drop the old difficulty CharField and promote difficulty_numeric to
    difficulty. Two operations in a single migration so they're atomic, but
    each prior migration (add column, data migration) remains independently
    reversible.
    """

    dependencies = [
        ('question', '0006_question_difficulty_data_migration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='question',
            name='difficulty',
        ),
        migrations.RenameField(
            model_name='question',
            old_name='difficulty_numeric',
            new_name='difficulty',
        ),
    ]