import pytest
from django.db import connection


@pytest.mark.django_db
def test_postgresql_connection_and_transaction_rollback():
    """Exercise the actual test database/driver, not a SQLite or mocked substitute."""
    from django.db import transaction

    assert connection.vendor == "postgresql"
    with connection.cursor() as cursor:
        cursor.execute("SHOW server_version_num")
        assert int(cursor.fetchone()[0]) >= 170000
        cursor.execute("CREATE TEMPORARY TABLE s004_probe (value integer NOT NULL)")
    with pytest.raises(ValueError, match="roll back probe"):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("INSERT INTO s004_probe VALUES (1)")
            raise ValueError("roll back probe")
    with connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM s004_probe")
        assert cursor.fetchone()[0] == 0
        cursor.execute("DROP TABLE s004_probe")
