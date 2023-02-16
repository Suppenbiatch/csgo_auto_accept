import os.path
import sqlite3
import time

from typing import Optional

__all__ = ['create_table', 'wait_until']


def wait_until(somepredicate, timeout: float, period: float = 0.25, *args, **kwargs):
  must_end = time.time() + timeout
  while time.time() < must_end:
    if somepredicate(*args, **kwargs): return True
    time.sleep(period)
  return False


def create_table(db_path, first_sharecode: Optional[str], steam_id: Optional[int]):
    if os.path.isfile(db_path):
        return
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS matches (
    sharecode   TEXT    UNIQUE
                        NOT NULL,
    id          INTEGER,
    map         TEXT,
    team_score  INTEGER,
    enemy_score INTEGER,
    match_time  INTEGER,
    wait_time   INTEGER,
    afk_time    INTEGER,
    mvps        INTEGER,
    points      INTEGER,
    outcome     TEXT,
    start_team  TEXT,
    kills       INTEGER,
    assists     INTEGER,
    deaths      INTEGER,
    [5k]        INTEGER,
    [4k]        INTEGER,
    [3k]        INTEGER,
    [2k]        INTEGER,
    [1k]        INTEGER,
    KD          REAL,
    ADR         INTEGER,
    HS          REAL,
    KAST        REAL,
    HLTV1       REAL,
    HLTV2       REAL,
    rank        INTEGER,
    rank_change TEXT,
    name        TEXT,
    server      TEXT,
    steam_id    INTEGER NOT NULL,
    timestamp   REAL    NOT NULL,
    error       BOOLEAN DEFAULT (0) 
);
""")
        if first_sharecode is not None:
            db.execute("""INSERT INTO matches (sharecode, steam_id, timestamp) VALUES (?, ?, ?)""", (first_sharecode, steam_id, 0.0))
        db.commit()
