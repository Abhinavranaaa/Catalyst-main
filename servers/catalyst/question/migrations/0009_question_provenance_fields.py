from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('question', '0008_question_bloom_level'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='difficulty_source',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('manual', 'Manual'),
                    ('irt', 'IRT'),
                    ('llm_estimated', 'LLM Estimated'),
                ],
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='bloom_level_source',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('manual', 'Manual'),
                    ('llm_classified', 'LLM Classified'),
                ],
                blank=True,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='question',
            name='explanation_source',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('manual', 'Manual'),
                    ('llm_generated', 'LLM Generated'),
                ],
                blank=True,
                null=True,
            ),
        ),
    ]