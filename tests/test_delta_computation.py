"""Tests for the simplified digest delta computation."""

from datetime import datetime

from exim_agent.application.compliance_service.digest_service import compute_deltas


class TestDeltaComputation:
    def test_new_monitoring_detected(self):
        previous_snapshots = {}
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {"tiles": []},
                "generated_at": datetime.utcnow().isoformat(),
            }
        }

        changes = compute_deltas(previous_snapshots, current_snapshots)

        assert len(changes) == 1
        assert changes[0]["change_type"] == "new_monitoring"
        assert changes[0]["priority"] == "medium"

    def test_risk_escalation_detected(self):
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {"tiles": [{"risk_level": "low"}]}
            }
        }
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {"tiles": [{"risk_level": "high"}]},
                "generated_at": datetime.utcnow().isoformat(),
            }
        }

        changes = compute_deltas(previous_snapshots, current_snapshots)

        assert any(change["change_type"] == "risk_escalation" for change in changes)

    def test_new_requirement_detected(self):
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {"tiles": [{"risk_level": "low"}]}
            }
        }
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {"tiles": [{"risk_level": "medium"}]},
                "generated_at": datetime.utcnow().isoformat(),
            }
        }

        changes = compute_deltas(previous_snapshots, current_snapshots)

        assert any(change["change_type"] == "new_requirement" for change in changes)
