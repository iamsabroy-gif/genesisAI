"""
Episodic Memory & Mentorship Heuristic Ingestion for Project Genesis.
Implements the SQLite-backed heuristic storage and retrieval from algo.md Section 7.
"""

import sqlite3
import re
from typing import List, Dict, Any, Optional
from genesis.config import GENESIS_HOME

MEMORY_DB_PATH = GENESIS_HOME / "memory.db"


class MentorshipMemory:
    """Manages long-term storage of user guidance heuristics and repo rules."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(MEMORY_DB_PATH)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS heuristics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT NOT NULL,
                    forbidden TEXT,
                    preferred TEXT NOT NULL,
                    rationale TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def record_heuristic(
        self,
        domain: str,
        preferred: str,
        forbidden: Optional[str] = None,
        rationale: Optional[str] = None,
    ) -> int:
        """Store a human guidance heuristic in long-term memory."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO heuristics (domain, forbidden, preferred, rationale)
                VALUES (?, ?, ?, ?)
                """,
                (domain, forbidden or "", preferred, rationale or ""),
            )
            conn.commit()
            return cur.lastrowid

    def retrieve_heuristics(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Keyword and domain-matched heuristic recall.
        Matches domain or preferred tokens against the user query.
        """
        query_words = set(re.findall(r"\w+", query.lower()))
        results = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM heuristics ORDER BY id DESC").fetchall()
            for r in rows:
                domain_words = set(re.findall(r"\w+", r["domain"].lower()))
                pref_words = set(re.findall(r"\w+", r["preferred"].lower()))
                combined = domain_words.union(pref_words)
                
                # Check overlap: if query is empty (like for !RULES), match all rules; otherwise check word overlap or global domain
                if not query_words or combined.intersection(query_words) or r["domain"] == "global":
                    results.append({
                        "id": r["id"],
                        "domain": r["domain"],
                        "forbidden": r["forbidden"],
                        "preferred": r["preferred"],
                        "rationale": r["rationale"],
                    })
                if len(results) >= limit:
                    break

        return results

    def format_heuristics_context(self, query: str) -> str:
        """Formats relevant stored mentorship rules into an injection string for C_memory."""
        heuristics = self.retrieve_heuristics(query)
        if not heuristics:
            return ""

        lines = ["[Mentorship Memory & Inviolable Rules from Past Guidance]:"]
        for h in heuristics:
            entry = f"• Domain: {h['domain']} | Preferred: {h['preferred']}"
            if h["forbidden"]:
                entry += f" | Forbidden: {h['forbidden']}"
            if h["rationale"]:
                entry += f" (Rationale: {h['rationale']})"
            lines.append(entry)

        return "\n".join(lines)

    # ── C3: RAG over Past Session Trajectories ──────────────────────────────
    def retrieve_past_trajectories(self, query: str, limit: int = 2) -> List[Dict[str, Any]]:
        """
        C3: Semantic and keyword recall over completed past session trajectories.
        Scans TRAJECTORY_DIR for successful sessions whose user prompt or final answer
        overlaps with the current query, providing cross-session contextual memory.
        """
        query_words = set(re.findall(r"\w+", query.lower()))
        # Skip small or trivial queries
        stop_words = {"what", "how", "why", "the", "and", "for", "with", "this", "that", "from"}
        meaningful_words = query_words - stop_words
        if len(meaningful_words) < 2:
            return []

        import json
        from genesis.config import TRAJECTORY_DIR
        matched = []

        for p in sorted(TRAJECTORY_DIR.glob("session_*.json"), reverse=True)[:30]:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if data.get("outcome") != "completed":
                    continue

                trajectory = data.get("trajectory", [])
                user_prompts = [
                    str(s.get("content", ""))
                    for s in trajectory if s.get("role") == "user"
                ]
                assistant_answers = [
                    str(s.get("content", ""))
                    for s in trajectory if s.get("role") == "assistant"
                ]

                full_session_text = " ".join(user_prompts + assistant_answers).lower()
                overlap = sum(1 for w in meaningful_words if w in full_session_text)
                score = overlap / len(meaningful_words)

                if score >= 0.4:
                    first_goal = user_prompts[0][:200] if user_prompts else ""
                    last_ans = assistant_answers[-1][:400] if assistant_answers else ""
                    matched.append({
                        "session_id": data.get("session_id", p.stem),
                        "score": score,
                        "goal": first_goal,
                        "solution_summary": last_ans,
                    })
                    if len(matched) >= limit:
                        break
            except Exception:
                continue

        return matched

    def format_combined_context(self, query: str) -> str:
        """
        C3 + Mentorship: Formats both mentorship heuristics AND relevant past session
        knowledge to inject into the user prompt anchor.
        """
        sections = []
        heuristics_str = self.format_heuristics_context(query)
        if heuristics_str:
            sections.append(heuristics_str)

        past_sessions = self.retrieve_past_trajectories(query)
        if past_sessions:
            p_lines = ["[Cross-Session Memory — Relevant Past Solutions]:"]
            for s in past_sessions:
                p_lines.append(f"• Past Goal: {s['goal']}")
                if s['solution_summary']:
                    p_lines.append(f"  Outcome: {s['solution_summary']}")
            sections.append("\n".join(p_lines))

        return "\n\n".join(sections)

