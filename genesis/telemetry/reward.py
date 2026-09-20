"""
Trajectory Evaluation and Multi-Objective Reward Scoring for Project Genesis.
Implements the mathematical formulation R(tau) from algo.md.
"""

from typing import Dict, Any, Tuple


def evaluate_trajectory(
    trajectory_data: Dict[str, Any],
    tests_passed: bool = False,
    user_feedback: int = 0,       # +1 (Accepted), 0 (Neutral), -1 (Rejected)
    syntax_error_present: bool = False,
    expected_turns: int = 4,
) -> Tuple[float, str]:
    """
    Computes heuristic reward R(tau) and routes into dataset categories:
    - 'sft_gold' (R >= 0.80)
    - 'self_correction' (R >= 0.50 with recovery)
    - 'dpo_candidate' (user feedback negative or rejected)
    - 'unranked'
    """
    w1 = 0.40  # Test pass indicator
    w2 = 0.35  # User acceptance
    w3 = 0.15  # Turn efficiency
    w4 = 0.10  # Syntax error penalty

    steps = trajectory_data.get("trajectory", [])
    actual_turns = max(1, len([s for s in steps if s.get("role") == "assistant_tool_call"]))

    i_tests = 1.0 if tests_passed else 0.0
    u_norm = max(-1.0, min(1.0, float(user_feedback)))
    u_score = (u_norm + 1.0) / 2.0  # Normalize [-1, 1] to [0, 1]

    # Efficiency ratio: 1.0 if actual <= expected, decreases if circular
    eff_ratio = min(1.0, float(expected_turns) / float(actual_turns))
    i_syntax = 1.0 if syntax_error_present else 0.0

    r = (w1 * i_tests) + (w2 * u_score) + (w3 * eff_ratio) - (w4 * i_syntax)
    reward = round(max(0.0, min(1.0, r)), 4)

    # Check for self-correction signal
    has_test_failure = any(
        "exit code" in str(s.get("content", "")).lower() and "exit code 0" not in str(s.get("content", "")).lower()
        for s in steps if s.get("role") == "tool_observation"
    )

    if reward >= 0.80 and tests_passed and u_norm >= 0:
        routing = "sft_gold"
    elif reward >= 0.50 and has_test_failure and tests_passed:
        routing = "self_correction"
    elif u_norm < 0:
        routing = "dpo_candidate"
    else:
        routing = "unranked"

    return reward, routing
