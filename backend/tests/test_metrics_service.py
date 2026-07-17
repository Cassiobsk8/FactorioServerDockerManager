from backend.services.metrics_service import get_process_metrics


def test_get_process_metrics_returns_expected_fields():
    metrics = get_process_metrics(None)

    for field in ("cpu_percent", "ram_used_mb", "ram_total_mb", "uptime_seconds", "disk_used_mb", "disk_total_mb"):
        assert field in metrics, f"missing metric field: {field}"

    for field in ("ram_used_mb", "ram_total_mb", "disk_used_mb", "disk_total_mb"):
        assert isinstance(metrics[field], (int, float)), f"{field} is not numeric"

    # Old field names must no longer be present
    assert "ram_mb" not in metrics
    assert "disk_usage_mb" not in metrics

    # Totals should be non-negative; used cannot exceed total when known
    assert metrics["ram_total_mb"] >= 0
    assert metrics["disk_total_mb"] >= 0
    assert metrics["ram_used_mb"] <= metrics["ram_total_mb"] or metrics["ram_total_mb"] == 0
    assert metrics["disk_used_mb"] <= metrics["disk_total_mb"] or metrics["disk_total_mb"] == 0
