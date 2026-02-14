
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('roadmap', '0010_roadmap_search_vector_en_roadmap_search_vector_smpl_and_more'),
    ]
    
    operations = [
        migrations.RunSQL(
            """
            DROP TRIGGER IF EXISTS roadmap_search_vector_trigger ON roadmaps;
            DROP FUNCTION IF EXISTS roadmap_search_vector_update();

            CREATE OR REPLACE FUNCTION roadmap_search_vector_update()
            RETURNS trigger AS $$
            BEGIN

                NEW.search_vector_en :=
                    setweight(
                        to_tsvector('english', coalesce(NEW.title, '')),
                        'A'
                    )
                    ||
                    setweight(
                        to_tsvector('english', coalesce(NEW.description, '')),
                        'B'
                    );

                NEW.search_vector_smpl :=
                    setweight(
                        to_tsvector('simple', coalesce(NEW.title, '')),
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

            CREATE TRIGGER roadmap_search_vector_trigger
            BEFORE INSERT OR UPDATE
            ON roadmaps
            FOR EACH ROW
            EXECUTE FUNCTION roadmap_search_vector_update();
            """,
            reverse_sql="""
            DROP TRIGGER IF EXISTS roadmap_search_vector_trigger ON roadmaps;
            DROP FUNCTION IF EXISTS roadmap_search_vector_update();
            """,
        ),
    ]
