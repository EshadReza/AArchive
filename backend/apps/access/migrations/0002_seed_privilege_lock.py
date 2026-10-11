from django.db import migrations


def seed(apps, schema_editor):
    apps.get_model("access", "PrivilegeLock").objects.using(
        schema_editor.connection.alias
    ).get_or_create(pk=1)


class Migration(migrations.Migration):
    dependencies = [("access", "0001_initial"), ("audit", "0002_append_only")]
    operations = [migrations.RunPython(seed, reverse_code=migrations.RunPython.noop)]
