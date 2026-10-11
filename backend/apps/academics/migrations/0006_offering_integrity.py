from django.db import migrations

FORWARD = """
CREATE FUNCTION academics_check_offering() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND (
        ROW(NEW.id, NEW.course_id, NEW.batch_id, NEW.term_id, NEW.section_id,
            NEW.created_by_id, NEW.created_at) IS DISTINCT FROM
        ROW(OLD.id, OLD.course_id, OLD.batch_id, OLD.term_id, OLD.section_id,
            OLD.created_by_id, OLD.created_at)) THEN
        RAISE EXCEPTION 'Offering identity and authorship are immutable' USING ERRCODE = '23514';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM academics_course c, academics_batch b, academics_term t, academics_section s
        WHERE c.id=NEW.course_id AND b.id=NEW.batch_id AND t.id=NEW.term_id
          AND s.id=NEW.section_id AND c.department_id=b.department_id
          AND t.batch_id=b.id AND s.batch_id=b.id
    ) THEN
        RAISE EXCEPTION 'Offering parents must match' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER academics_offering_integrity BEFORE INSERT OR UPDATE ON academics_offering
FOR EACH ROW EXECUTE FUNCTION academics_check_offering();
CREATE FUNCTION academics_retain_teacher_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        RAISE EXCEPTION 'Teacher assignment history cannot be deleted' USING ERRCODE = '23514';
    END IF;
    IF ROW(NEW.id,NEW.offering_id,NEW.teacher_id,NEW.assigned_by_id,NEW.assigned_at)
       IS DISTINCT FROM ROW(OLD.id,OLD.offering_id,OLD.teacher_id,
                            OLD.assigned_by_id,OLD.assigned_at)
       OR (OLD.ended_at IS NOT NULL AND ROW(NEW.ended_at,NEW.removed_by_id)
           IS DISTINCT FROM ROW(OLD.ended_at,OLD.removed_by_id)) THEN
        RAISE EXCEPTION 'Teacher assignment history is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER academics_teacher_history BEFORE UPDATE OR DELETE ON academics_teacherassignment
FOR EACH ROW EXECUTE FUNCTION academics_retain_teacher_history();
"""
REVERSE = """
DROP TRIGGER academics_teacher_history ON academics_teacherassignment;
DROP FUNCTION academics_retain_teacher_history();
DROP TRIGGER academics_offering_integrity ON academics_offering;
DROP FUNCTION academics_check_offering();
"""


class Migration(migrations.Migration):
    dependencies = [("academics", "0005_offering_teacherassignment_and_more")]
    operations = [migrations.RunSQL(FORWARD, REVERSE)]
