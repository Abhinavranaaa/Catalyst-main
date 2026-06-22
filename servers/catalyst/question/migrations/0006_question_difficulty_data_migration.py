from django.db import migrations


def forwards(apps, schema_editor):
    schema_editor.execute("""
        UPDATE questions
        SET difficulty_numeric = CASE LOWER(TRIM(difficulty))
            WHEN 'easy'   THEN 1
            WHEN 'medium' THEN 3
            WHEN 'hard'   THEN 5
            ELSE NULL
        END
        WHERE difficulty IS NOT NULL AND difficulty <> ''
    """)


def backwards(apps, schema_editor):
    schema_editor.execute("""
        UPDATE questions
        SET difficulty = CASE difficulty_numeric
            WHEN 1 THEN 'easy'
            WHEN 3 THEN 'medium'
            WHEN 5 THEN 'hard'
            ELSE ''
        END
        WHERE difficulty_numeric IS NOT NULL
    """)


class Migration(migrations.Migration):

    dependencies = [
        ('question', '0005_question_difficulty_numeric'),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=backwards),
    ]