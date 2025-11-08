"""Tests for delta computation with tile-level comparison."""

import pytest
from datetime import datetime
from exim_agent.application.zenml_pipelines.weekly_pulse import compute_deltas


class TestDeltaComputation:
    """Tests for tile-level delta computation."""
    
    def test_new_monitoring_detected(self):
        """Test detection of new SKU+Lane combinations."""
        previous_snapshots = {}
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00 - Free",
                            "details_md": "No issues"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "new_monitoring"
        assert changes[0]["priority"] == "medium"
        assert "SKU-001:CNSHA-USLAX-ocean" in changes[0]["sku_lane_key"]
    
    def test_status_escalation_clear_to_attention(self):
        """Test detection of status change from clear to attention."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "sanctions_screening": {
                            "status": "clear",
                            "headline": "No sanctions issues",
                            "details_md": "All clear"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "sanctions_screening": {
                            "status": "attention",
                            "headline": "Supplier requires review",
                            "details_md": "Enhanced due diligence needed"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "status_change"
        assert changes[0]["priority"] == "medium"
        assert changes[0]["details"]["previous_status"] == "clear"
        assert changes[0]["details"]["current_status"] == "attention"
    
    def test_status_escalation_attention_to_action(self):
        """Test detection of status change from attention to action."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "refusal_history": {
                            "status": "attention",
                            "headline": "2 Import Refusals",
                            "details_md": "Monitor closely"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "refusal_history": {
                            "status": "action",
                            "headline": "5 Import Refusals",
                            "details_md": "Immediate action required"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "status_change"
        assert changes[0]["priority"] == "high"
        assert changes[0]["details"]["current_status"] == "action"
    
    def test_risk_escalation_low_to_high(self):
        """Test detection of risk level escalation."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "risk_level": "low",
                            "details_md": "Standard classification"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "attention",
                            "headline": "HTS 8517.12.00 - Duty Change",
                            "risk_level": "high",
                            "details_md": "Significant duty increase"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        # Should detect both status change and risk escalation
        assert len(changes) >= 1
        
        risk_changes = [c for c in changes if c["change_type"] == "risk_escalation"]
        assert len(risk_changes) == 1
        assert risk_changes[0]["priority"] == "high"
        assert risk_changes[0]["details"]["previous_risk"] == "low"
        assert risk_changes[0]["details"]["current_risk"] == "high"
    
    def test_new_tile_detected(self):
        """Test detection of new compliance area tiles."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "details_md": "Standard"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "details_md": "Standard"
                        },
                        "sanctions_screening": {
                            "status": "attention",
                            "headline": "New sanctions alert",
                            "details_md": "Requires review"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "new_requirement"
        assert changes[0]["priority"] == "medium"
        assert "sanctions_screening" in changes[0]["description"]
    
    def test_headline_change_with_attention_status(self):
        """Test detection of headline changes for attention-level tiles."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "cbp_rulings": {
                            "status": "attention",
                            "headline": "2 Relevant Rulings",
                            "details_md": "Review recommended"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "cbp_rulings": {
                            "status": "attention",
                            "headline": "3 Relevant Rulings - New Guidance",
                            "details_md": "Updated guidance available"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "new_monitoring"
        assert changes[0]["priority"] == "low"
        assert "Updated information" in changes[0]["description"]
    
    def test_multiple_changes_same_sku_lane(self):
        """Test detection of multiple changes in same SKU+Lane."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "details_md": "Standard"
                        },
                        "sanctions_screening": {
                            "status": "clear",
                            "headline": "No issues",
                            "details_md": "All clear"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "attention",
                            "headline": "HTS 8517.12.00 - Rate Change",
                            "details_md": "Duty rate updated"
                        },
                        "sanctions_screening": {
                            "status": "action",
                            "headline": "Sanctions match found",
                            "details_md": "Immediate review required"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        # Should detect status changes for both tiles
        assert len(changes) == 2
        
        # Check that both tiles are represented
        tile_names = [c["details"]["tile_name"] for c in changes]
        assert "hts_classification" in tile_names
        assert "sanctions_screening" in tile_names
        
        # Check priorities
        high_priority_changes = [c for c in changes if c["priority"] == "high"]
        assert len(high_priority_changes) == 1  # sanctions_screening to action
    
    def test_no_changes_detected(self):
        """Test when no changes occur between snapshots."""
        snapshot_data = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "details_md": "Standard"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        previous_snapshots = snapshot_data.copy()
        current_snapshots = snapshot_data.copy()
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        # No changes should be detected
        assert len(changes) == 0
    
    def test_removed_tile_detected(self):
        """Test detection of removed compliance area tiles."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "details_md": "Standard"
                        },
                        "sanctions_screening": {
                            "status": "clear",
                            "headline": "No issues",
                            "details_md": "All clear"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "hts_classification": {
                            "status": "clear",
                            "headline": "HTS 8517.12.00",
                            "details_md": "Standard"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "new_monitoring"
        assert changes[0]["priority"] == "low"
        assert "no longer monitored" in changes[0]["description"]
    
    def test_action_required_status_variant(self):
        """Test handling of action_required status variant."""
        previous_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "sanctions_screening": {
                            "status": "clear",
                            "headline": "No issues",
                            "details_md": "All clear"
                        }
                    }
                }
            }
        }
        
        current_snapshots = {
            "SKU-001:CNSHA-USLAX-ocean": {
                "snapshot": {
                    "tiles": {
                        "sanctions_screening": {
                            "status": "action_required",
                            "headline": "Sanctions match",
                            "details_md": "Action needed"
                        }
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
        }
        
        changes = compute_deltas(previous_snapshots, current_snapshots)
        
        assert len(changes) == 1
        assert changes[0]["change_type"] == "status_change"
        assert changes[0]["priority"] == "high"
        assert changes[0]["details"]["current_status"] == "action_required"
