from app.control.account.enums import QuotaSource
from app.control.account.models import QuotaWindow
from app.control.account.quota_defaults import infer_pool


def _window(total: int) -> QuotaWindow:
    return QuotaWindow(
        remaining=total,
        total=total,
        window_seconds=7_200,
        reset_at=None,
        synced_at=None,
        source=QuotaSource.DEFAULT,
    )


def test_infer_pool_recognizes_lite_auto_total():
    windows = {0: _window(25)}

    assert infer_pool(windows, fallback="super") == "lite"


def test_infer_pool_keeps_fallback_when_auto_window_is_missing():
    assert infer_pool({}, fallback="super") == "super"
