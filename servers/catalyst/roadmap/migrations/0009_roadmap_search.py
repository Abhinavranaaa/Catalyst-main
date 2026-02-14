from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('roadmap', '0008_roadmap_avg_difficulty'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE FUNCTION roadmap_search_vector_update() RETURNS trigger AS $$
            BEGIN

                -- English search vector (stemming enabled)
                NEW.search_vector_en :=
                    setweight(
                        to_tsvector(
                            'english',
                            coalesce(NEW.title, '')
                        ),
                        'A'
                    )
                    ||
                    setweight(
                        to_tsvector(
                            'english',
                            coalesce(NEW.description, '')
                        ),
                        'B'
                    );

                -- Simple search vector (good for tags/topics)
                NEW.search_vector_smpl :=
                    setweight(
                        to_tsvector(
                            'simple',
                            coalesce(NEW.title, '')
                        ),
                        'A'
                    )
                    ||
                    setweight(
                        to_tsvector(
                            'simple',
                            coalesce(array_to_string(NEW.topics, ' '), '')
                        ),
                        'A'
                    );

                RETURN NEW;
            END
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="""
            DROP FUNCTION IF EXISTS roadmap_search_vector_update;
            """,
        ),

        migrations.RunSQL(
            """
            CREATE TRIGGER roadmap_search_vector_trigger
            BEFORE INSERT OR UPDATE ON roadmaps
            FOR EACH ROW
            EXECUTE FUNCTION roadmap_search_vector_update();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS roadmap_search_vector_trigger
            ON roadmaps;
            """,
        ),
    ]
