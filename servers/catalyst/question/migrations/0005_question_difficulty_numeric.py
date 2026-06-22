from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('question', '0004_question_enrichment_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='difficulty_numeric',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
