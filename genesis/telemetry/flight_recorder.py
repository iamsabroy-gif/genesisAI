"""
Flight Recorder Telemetry Engine for Project Genesis.
Captures full cognitive execution traces for dataset harvesting and fine-tuning.
"""

import json
import time
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from genesis.config import TRAJECTORY_DIR
from genesis.telemetry.reward import evaluate_trajectory


class FlightRecorder:
    """Records every thought, tool invocation, observation, and outcome."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.start_time = datetime.datetime.now().isoformat()
        self.trajectory: List[Dict[str, Any]] = []
        self.tests_passed: bool = False
        self.user_feedback: int = 0  # +1 (Accepted), 0 (Neutral), -1 (Rejected)
        self.purged: bool = False

    def mark_purged(self):
        """Mark active session as purged/invalidated so curator ignores it."""
        self.purged = True

    def record_step(self, role: str, content: Any, metadata: Optional[Dict[str, Any]] = None):
        """Append a discrete step to the trajectory history."""
        step = {
            "timestamp": time.time(),
            "role": role,
            "content": content,
        }
        if metadata:
            step["metadata"] = metadata
        self.trajectory.append(step)

    def set_test_status(self, passed: bool):
        """Record whether tests/verification passed."""
        self.tests_passed = passed

    def set_feedback(self, feedback: int):
        """Record explicit user feedback (+1, 0, -1)."""
        self.user_feedback = feedback

    def finalize(self, outcome: str = "completed") -> Path:
        """Score trajectory and serialize to JSONL / JSON in TRAJECTORY_DIR."""
        final_outcome = "purged" if self.purged else outcome
        raw_record = {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": datetime.datetime.now().isoformat(),
            "outcome": final_outcome,
            "trajectory": self.trajectory,
        }

        # Calculate reward score and routing category
        reward, routing = evaluate_trajectory(
            raw_record,
            tests_passed=self.tests_passed,
            user_feedback=self.user_feedback,
        )

        raw_record["reward_score"] = reward
        raw_record["routing"] = routing

        output_path = TRAJECTORY_DIR / f"session_{self.session_id[:8]}.json"
        output_path.write_text(json.dumps(raw_record, indent=2), encoding="utf-8")
        return output_path
