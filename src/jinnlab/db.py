from __future__ import annotations
import csv
import json
import sqlite3
from pathlib import Path
from typing import Iterable

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS experiments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    experiment_type TEXT NOT NULL,
    player1 TEXT,
    player2 TEXT,
    winner TEXT,
    score1 REAL,
    score2 REAL,
    turns INTEGER,
    repetitions INTEGER,
    seed INTEGER,
    metadata TEXT
);
CREATE TABLE IF NOT EXISTS strategy_notes (
    strategy TEXT PRIMARY KEY,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS tournament_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL,
    rank INTEGER NOT NULL,
    strategy TEXT NOT NULL,
    score REAL NOT NULL,
    FOREIGN KEY(experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS experiment_notes (
    experiment_id INTEGER PRIMARY KEY,
    hypothesis TEXT NOT NULL DEFAULT '',
    observation TEXT NOT NULL DEFAULT '',
    conclusion TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS strategy_designs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    family_name TEXT NOT NULL,
    version INTEGER NOT NULL,
    display_name TEXT NOT NULL UNIQUE,
    definition_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(family_name, version)
);
CREATE INDEX IF NOT EXISTS idx_experiments_created ON experiments(created_at);
CREATE INDEX IF NOT EXISTS idx_experiments_players ON experiments(player1, player2);
CREATE INDEX IF NOT EXISTS idx_tournament_exp ON tournament_scores(experiment_id);
CREATE INDEX IF NOT EXISTS idx_strategy_notes_updated ON strategy_notes(updated_at);
CREATE INDEX IF NOT EXISTS idx_design_family ON strategy_designs(family_name, version);
"""

class ResultsDB:
    def __init__(self, path: Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con: con.executescript(SCHEMA)

    def connect(self):
        con = sqlite3.connect(self.path); con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON"); return con

    def add_experiment(self, **fields) -> int:
        columns = [k for k, v in fields.items() if v is not None]
        values = [fields[k] for k in columns]
        q = f"INSERT INTO experiments ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
        with self.connect() as con:
            cur = con.execute(q, values); return int(cur.lastrowid)

    def get_experiment(self, experiment_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM experiments WHERE id=?", (experiment_id,)).fetchone()

    def add_tournament_scores(self, experiment_id: int, rows: Iterable[tuple[int, str, float]]) -> None:
        with self.connect() as con:
            con.executemany("INSERT INTO tournament_scores(experiment_id, rank, strategy, score) VALUES (?,?,?,?)", rows)

    def tournament_scores(self, experiment_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM tournament_scores WHERE experiment_id=? ORDER BY rank", (experiment_id,)).fetchall()

    def save_strategy_note(self, strategy: str, note: str) -> None:
        with self.connect() as con:
            con.execute("""INSERT INTO strategy_notes(strategy,note,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(strategy) DO UPDATE SET note=excluded.note,updated_at=CURRENT_TIMESTAMP""", (strategy, note))

    def get_strategy_note(self, strategy: str) -> str:
        with self.connect() as con:
            row = con.execute("SELECT note FROM strategy_notes WHERE strategy=?", (strategy,)).fetchone()
        return row["note"] if row else ""

    def save_experiment_note(self, experiment_id: int, hypothesis: str, observation: str, conclusion: str) -> None:
        with self.connect() as con:
            con.execute("""INSERT INTO experiment_notes(experiment_id,hypothesis,observation,conclusion,updated_at)
                VALUES(?,?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(experiment_id) DO UPDATE SET hypothesis=excluded.hypothesis,
                observation=excluded.observation,conclusion=excluded.conclusion,updated_at=CURRENT_TIMESTAMP""",
                (experiment_id, hypothesis, observation, conclusion))

    def get_experiment_note(self, experiment_id: int):
        with self.connect() as con:
            return con.execute("SELECT * FROM experiment_notes WHERE experiment_id=?", (experiment_id,)).fetchone()

    def save_strategy_design(self, family_name: str, definition: dict) -> str:
        family = family_name.strip() or "Custom"
        with self.connect() as con:
            row = con.execute("SELECT COALESCE(MAX(version),0)+1 FROM strategy_designs WHERE family_name=?", (family,)).fetchone()
            version = int(row[0]); display = f"{family} v{version}"
            definition = dict(definition); definition["display_name"] = display
            con.execute("INSERT INTO strategy_designs(family_name,version,display_name,definition_json) VALUES(?,?,?,?)",
                        (family, version, display, json.dumps(definition)))
        return display

    def strategy_designs(self):
        with self.connect() as con:
            rows = con.execute("SELECT * FROM strategy_designs ORDER BY family_name,version").fetchall()
        out=[]
        for r in rows:
            d=json.loads(r["definition_json"]); d.update({"family_name":r["family_name"],"version":r["version"],"display_name":r["display_name"]}); out.append(d)
        return out

    def recent(self, limit: int = 100):
        with self.connect() as con:
            return con.execute("SELECT * FROM experiments ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

    def summary(self):
        with self.connect() as con:
            total = con.execute("SELECT COUNT(*) FROM experiments").fetchone()[0]
            by_type = con.execute("SELECT experiment_type, COUNT(*) n FROM experiments GROUP BY experiment_type ORDER BY n DESC").fetchall()
            winners = con.execute("SELECT winner, COUNT(*) n FROM experiments WHERE winner IS NOT NULL GROUP BY winner ORDER BY n DESC LIMIT 8").fetchall()
            avg_margin = con.execute("SELECT AVG(ABS(score1-score2)) FROM experiments WHERE score1 IS NOT NULL AND score2 IS NOT NULL").fetchone()[0]
        return {"total": total, "by_type": by_type, "winners": winners, "avg_margin": avg_margin or 0.0}

    def export_csv(self, path: Path) -> int:
        rows = self.recent(1_000_000)
        if not rows: return 0
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(rows[0].keys()); w.writerows(tuple(r) for r in rows)
        return len(rows)
