from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('roadmap', '0019_dailysession'),
    ]

    operations = [
        # 1. Add subject with a temporary default so existing rows survive
        migrations.AddField(
            model_name='dailysession',
            name='subject',
            field=models.CharField(max_length=255, default='Operating Systems'),
            preserve_default=False,
        ),
        # 2. Add completion stats fields
        migrations.AddField(
            model_name='dailysession',
            name='completion_accuracy',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='dailysession',
            name='completion_questions',
            field=models.IntegerField(blank=True, null=True),
        ),
        # 3. Drop old unique constraint that references roadmap
        migrations.RemoveConstraint(
            model_name='dailysession',
            name='unique_daily_session_per_roadmap',
        ),
        # 4. Drop the roadmap FK
        migrations.RemoveField(
            model_name='dailysession',
            name='roadmap',
        ),
        # 5. Add new unique constraint scoped to (user, subject, date)
        migrations.AddConstraint(
            model_name='dailysession',
            constraint=models.UniqueConstraint(
                fields=['user', 'subject', 'date'],
                name='unique_daily_session_per_subject',
            ),
        ),
    ]
