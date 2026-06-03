from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.schemas import CardType, InteractiveContextPackage, SessionMemory


class ContextManager:
    """Builds compact context packages for follow-up questions with SQLite persistence."""

    def __init__(self, db_path: str | Path = "workspace/sensei_sessions.db", workspace_dir: str | Path = "workspace") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace_dir = Path(workspace_dir)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._conn.commit()

    def get_memory(self, session_id: str) -> SessionMemory | None:
        row = self._conn.execute(
            "SELECT data FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        if row is None:
            return None
        return SessionMemory.model_validate_json(row[0])

    def update_memory(self, session_id: str, memory: SessionMemory) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO sessions (session_id, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (session_id, memory.model_dump_json()),
        )
        self._conn.commit()

    def _load_job_data(self, job_id: str) -> dict:
        """Load paper skeleton and card data from workspace for context building."""
        run_dir = self.workspace_dir / "runs" / job_id
        data = {}
        for filename, key in [
            ("paper_skeleton.json", "skeleton"),
            ("cards/json/paper_card.json", "paper_card"),
            ("pattern_card.json", "pattern_card"),
            ("drill_card.json", "drill_card"),
        ]:
            path = run_dir / filename
            if path.exists():
                try:
                    data[key] = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass
        # Load formula cards
        json_dir = run_dir / "cards" / "json"
        if json_dir.exists():
            formula_cards = []
            for f in sorted(json_dir.glob("formula_card_*.json")):
                try:
                    formula_cards.append(json.loads(f.read_text(encoding="utf-8")))
                except Exception:
                    pass
            data["formula_cards"] = formula_cards
        return data

    def build_package(
        self,
        session_id: str,
        paper_id: str,
        card_id: str,
        card_type: CardType,
        selected_text: str,
        user_question: str,
    ) -> InteractiveContextPackage:
        memory = self.get_memory(session_id)
        if memory is None:
            memory = SessionMemory(
                session_id=session_id,
                paper_id=paper_id,
                user_profile={
                    "language": "zh",
                    "math_level": "weak",
                    "preferred_style": "concise_but_explain_clearly",
                },
            )
        memory.asked_questions.append(user_question)
        if selected_text:
            memory.confusing_items.append(selected_text)
        self.update_memory(session_id, memory)

        # Load actual paper data for context
        job_data = self._load_job_data(paper_id)
        skeleton = job_data.get("skeleton", {})
        paper_card = job_data.get("paper_card", {})

        # Build evidence chunks from skeleton
        evidence_chunks = []
        if skeleton:
            problem = skeleton.get("problem", {})
            if problem.get("plain"):
                evidence_chunks.append({
                    "evidence_ref": f"{paper_id}:problem",
                    "text": problem["plain"],
                })
            mechanism = skeleton.get("mechanism", {})
            if mechanism.get("plain"):
                evidence_chunks.append({
                    "evidence_ref": f"{paper_id}:mechanism",
                    "text": mechanism["plain"],
                })
        if selected_text:
            evidence_chunks.append({
                "evidence_ref": f"{paper_id}:selected",
                "text": selected_text,
            })

        # Build paper metadata
        paper_metadata = {
            "title": paper_card.get("paper_id", paper_id) if paper_card else paper_id,
            "paper_id": paper_id,
        }

        return InteractiveContextPackage(
            session_id=session_id,
            paper_id=paper_id,
            card_id=card_id,
            card_type=card_type,
            selected_text=selected_text,
            current_formula_id="eq001" if card_type == CardType.FORMULA_CARD else "",
            evidence_chunks=evidence_chunks,
            recent_chat_history=[],
            conversation_summary=f"用户正在学习论文 {paper_id}，围绕当前卡片追问。需中文、直觉优先、证据不足要标注。",
            paper_metadata=paper_metadata,
            user_profile=memory.user_profile,
            user_question=user_question,
        )
