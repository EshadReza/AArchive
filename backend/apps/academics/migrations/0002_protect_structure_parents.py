from django.db import migrations

FORWARD = """
CREATE FUNCTION academics_protect_structure() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_TABLE_NAME = 'academics_batch' THEN
        IF NEW.department_id IS DISTINCT FROM OLD.department_id THEN
            RAISE EXCEPTION 'Academic parents are immutable' USING ERRCODE = '23514';
        END IF;
    ELSE
        IF NEW.batch_id IS DISTINCT FROM OLD.batch_id THEN
            RAISE EXCEPTION 'Academic parents are immutable' USING ERRCODE = '23514';
        END IF;
    END IF;
    IF TG_TABLE_NAME = 'academics_section' THEN
        IF (OLD.label = 'ALL' AND (NEW.label <> 'ALL' OR NEW.archived))
           OR (OLD.label <> 'ALL' AND NEW.label = 'ALL') THEN
            RAISE EXCEPTION 'ALL section is reserved' USING ERRCODE = '23514';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER academics_batch_parent BEFORE UPDATE ON academics_batch
FOR EACH ROW EXECUTE FUNCTION academics_protect_structure();
CREATE TRIGGER academics_term_parent BEFORE UPDATE ON academics_term
FOR EACH ROW EXECUTE FUNCTION academics_protect_structure();
CREATE TRIGGER academics_section_parent BEFORE UPDATE ON academics_section
FOR EACH ROW EXECUTE FUNCTION academics_protect_structure();
"""
REVERSE = """
DROP TRIGGER academics_section_parent ON academics_section;
DROP TRIGGER academics_term_parent ON academics_term;
DROP TRIGGER academics_batch_parent ON academics_batch;
DROP FUNCTION academics_protect_structure();
"""


class Migration(migrations.Migration):
    dependencies = [("academics", "0001_initial")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
