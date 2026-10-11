from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("audit", "0001_initial")]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE FUNCTION audit_reject_mutation() RETURNS trigger
                LANGUAGE plpgsql AS $$
                BEGIN
                    RAISE EXCEPTION 'Audit entries are append-only'
                        USING ERRCODE = '23514';
                END;
                $$;
                CREATE TRIGGER audit_append_only
                    BEFORE UPDATE OR DELETE ON audit_auditlog
                    FOR EACH ROW EXECUTE FUNCTION audit_reject_mutation();
            """,
            reverse_sql="""
                DROP TRIGGER audit_append_only ON audit_auditlog;
                DROP FUNCTION audit_reject_mutation();
            """,
        ),
    ]
