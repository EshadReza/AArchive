from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("academics", "0003_course")]
    operations = [
        migrations.RunSQL(
            """
        CREATE FUNCTION academics_protect_course_department() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.department_id IS DISTINCT FROM OLD.department_id THEN
                RAISE EXCEPTION 'Course department is immutable' USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER academics_course_department BEFORE UPDATE ON academics_course
        FOR EACH ROW EXECUTE FUNCTION academics_protect_course_department();
        """,
            """
        DROP TRIGGER academics_course_department ON academics_course;
        DROP FUNCTION academics_protect_course_department();
        """,
        )
    ]
