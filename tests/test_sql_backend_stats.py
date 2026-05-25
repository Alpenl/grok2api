import sqlalchemy as sa
from sqlalchemy.dialects import mysql, postgresql

from app.control.account.backends import sql as sql_backend


def _compile(expr, dialect):
    return str(
        sa.select(expr).compile(
            dialect=dialect,
            compile_kwargs={"literal_binds": True},
        )
    )


def test_postgres_quota_remaining_expr_casts_text_to_jsonb():
    expr = sql_backend._quota_remaining_expr(  # type: ignore[attr-defined]
        sql_backend.accounts_table.c.quota_auto,
        "postgresql",
    )

    compiled = _compile(expr, postgresql.dialect())

    assert "CAST(accounts.quota_auto AS JSONB)" in compiled
    assert "remaining" in compiled
    assert "json_extract_path_text(accounts.quota_auto" not in compiled


def test_mysql_quota_remaining_expr_uses_json_extract():
    expr = sql_backend._quota_remaining_expr(  # type: ignore[attr-defined]
        sql_backend.accounts_table.c.quota_auto,
        "mysql",
    )

    compiled = _compile(expr, mysql.dialect())

    assert "json_extract" in compiled.lower()
    assert "quota_auto" in compiled
