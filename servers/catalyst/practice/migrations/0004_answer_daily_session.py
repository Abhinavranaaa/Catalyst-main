import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('practice', '0003_alter_answer_answered_at'),
        ('roadmap', '0020_dailysession_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='answer',
            name='daily_session',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                to='roadmap.dailysession',
            ),
        ),
    ]
