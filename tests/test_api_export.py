"""Tests cho lớp serialize payload JSON gửi sang web UI.

Giao diện lọc rule_findings theo kỳ đang chọn (`f.period === asof.period`), nên bất
kỳ dòng nào bị cắt lúc xuất đều làm cả kỳ đó trống trơn trên UI — trông hệt như
"không có vi phạm". Trước đây cap 8000 dòng đã âm thầm xóa 2023-01..2024-06 gồm
2631 vi phạm thật (975 CRITICAL) của 69 ngân hàng.
"""
from __future__ import annotations

import logging

import pandas as pd
import pytest

from src.api_export import _records
from src.utils import LOG


@pytest.fixture
def log_records():
    """Bắt log của logger 'bankrisk'.

    Logger này đặt propagate=False (utils.get_logger) nên caplog của pytest — vốn
    gắn handler vào root logger — không thấy gì. Phải gắn handler thẳng vào nó.
    """
    captured: list[str] = []

    class _Capture(logging.Handler):
        def emit(self, record):
            captured.append(record.getMessage())

    handler = _Capture(level=logging.WARNING)
    LOG.addHandler(handler)
    try:
        yield captured
    finally:
        LOG.removeHandler(handler)


def _findings(n_periods: int, per_period: int) -> pd.DataFrame:
    rows = []
    for p in range(n_periods):
        for i in range(per_period):
            rows.append({
                "bank_id": f"B{i}", "period": f"2023-{p + 1:02d}",
                "rule_id": "R1", "severity": "CRITICAL",
                "finding_type": "VIOLATION",
            })
    return pd.DataFrame(rows)


def test_records_keeps_every_period_when_uncapped():
    """Không cap -> không kỳ nào biến mất khỏi payload."""
    df = _findings(n_periods=6, per_period=100)
    recs = _records(df, name="rule_findings")
    assert len(recs) == len(df)
    assert len({r["period"] for r in recs}) == 6


def test_records_truncation_is_logged_not_silent(log_records):
    """Nếu vẫn còn cap ở đâu đó, việc cắt phải được ghi log rõ ràng."""
    df = _findings(n_periods=6, per_period=100)   # 600 dòng
    recs = _records(df, limit=250, name="rule_findings")
    assert len(recs) == 250
    assert any("rule_findings" in m and "350" in m for m in log_records), \
        f"phải cảnh báo đã cắt 350 dòng, log thực tế: {log_records}"


def test_records_no_warning_when_nothing_dropped(log_records):
    df = _findings(n_periods=2, per_period=10)     # 20 dòng
    _records(df, limit=8000, name="rule_findings")
    assert not log_records
