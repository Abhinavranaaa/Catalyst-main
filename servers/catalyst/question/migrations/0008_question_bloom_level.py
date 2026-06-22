from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('question', '0007_question_difficulty_replace_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='bloom_level',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]