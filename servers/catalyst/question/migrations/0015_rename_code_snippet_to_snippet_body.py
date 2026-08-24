from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('question', '0014_question_correct_value_question_response_type_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql='ALTER TABLE questions RENAME COLUMN code_snippet TO snippet_body;',
            reverse_sql='ALTER TABLE questions RENAME COLUMN snippet_body TO code_snippet;',
        ),
        migrations.RunSQL(
            sql='ALTER TABLE questions DROP COLUMN has_code_snippet;',
            reverse_sql='ALTER TABLE questions ADD COLUMN has_code_snippet boolean NOT NULL DEFAULT false;',
        ),
    ]
