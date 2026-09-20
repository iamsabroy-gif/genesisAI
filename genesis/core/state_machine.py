"""
Cognitive State Machine for Project Genesis.
Implements formal state definitions, Master override states, and transitions from algo.md.
"""

from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    PERCEIVE = auto()
    THINK = auto()
    ACT = auto()
    OBSERVE = auto()
    VERIFY = auto()
    CORRECT = auto()
    COMPLETE = auto()
    READ_ONLY_LOCK = auto()
    MASTER_HOLD = auto()
    TERMINATE = auto()


class CognitiveStateMachine:
    """Tracks and governs deterministic state transitions."""

    def __init__(self):
        self.state: State = State.IDLE
        self.retry_count: int = 0
        self.max_retries: int = 3
        self.transition_log = []

    def transition(self, next_state: State, reason: str = ""):
        old_state = self.state
        self.state = next_state
        entry = {
            "from": old_state.name,
            "to": next_state.name,
            "reason": reason,
        }
        self.transition_log.append(entry)

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def record_retry(self):
        self.retry_count += 1

    def reset_retries(self):
        self.retry_count = 0
