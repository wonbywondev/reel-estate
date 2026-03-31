import json
import sqlite3
from typing import Optional

from db.models import Room

DEFAULT_DB_PATH = "realestate.db"


class Database:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        assert self._conn is not None, "Database not initialized. Call init() first."
        return self._conn

    def init(self):
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                address         TEXT NOT NULL,
                floor           INTEGER,
                size_pyeong     REAL,
                deposit         INTEGER,
                monthly_rent    INTEGER,
                options         TEXT,
                year_built      INTEGER,
                lat             REAL,
                lng             REAL,
                subway_info     TEXT,
                video_path      TEXT,
                loan_available  INTEGER DEFAULT 0,
                agent_comment   TEXT,
                interior_paths  TEXT,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # 기존 DB에 새 컬럼 추가 (이미 있으면 무시)
        for col, definition in [
            ("loan_available", "INTEGER DEFAULT 0"),
            ("agent_comment", "TEXT"),
            ("interior_paths", "TEXT"),
        ]:
            try:
                self._conn.execute(f"ALTER TABLE rooms ADD COLUMN {col} {definition}")
            except sqlite3.OperationalError:
                pass  # 이미 존재
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()

    def insert_room(self, room: Room) -> int:
        cur = self.conn.execute(
            """INSERT INTO rooms
               (address, floor, size_pyeong, deposit, monthly_rent, options,
                year_built, lat, lng, subway_info, video_path,
                loan_available, agent_comment, interior_paths)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                room.address, room.floor, room.size_pyeong,
                room.deposit, room.monthly_rent,
                json.dumps(room.options, ensure_ascii=False),
                room.year_built, room.lat, room.lng,
                json.dumps(room.subway_info, ensure_ascii=False) if room.subway_info else None,
                room.video_path,
                int(room.loan_available),
                room.agent_comment,
                json.dumps(room.interior_paths, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return cur.lastrowid or 0

    def get_room(self, room_id: int) -> Optional[Room]:
        row = self.conn.execute(
            "SELECT * FROM rooms WHERE id = ?", (room_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_room(row)

    def list_rooms(self) -> list[Room]:
        rows = self.conn.execute(
            "SELECT * FROM rooms ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_room(r) for r in rows]

    def update_video_path(self, room_id: int, video_path: str):
        self.conn.execute(
            "UPDATE rooms SET video_path = ? WHERE id = ?", (video_path, room_id)
        )
        self.conn.commit()

    def delete_room(self, room_id: int) -> None:
        self.conn.execute("DELETE FROM rooms WHERE id = ?", (room_id,))
        self.conn.commit()

    def update_location(self, room_id: int, lat: float, lng: float, subway_info: dict):
        self.conn.execute(
            "UPDATE rooms SET lat=?, lng=?, subway_info=? WHERE id=?",
            (lat, lng, json.dumps(subway_info, ensure_ascii=False), room_id),
        )
        self.conn.commit()

    def _row_to_room(self, row: sqlite3.Row) -> Room:
        keys = row.keys()
        return Room(
            id=row["id"],
            address=row["address"],
            floor=row["floor"],
            size_pyeong=row["size_pyeong"],
            deposit=row["deposit"],
            monthly_rent=row["monthly_rent"],
            options=json.loads(row["options"]) if row["options"] else [],
            year_built=row["year_built"],
            lat=row["lat"],
            lng=row["lng"],
            subway_info=json.loads(row["subway_info"]) if row["subway_info"] else None,
            video_path=row["video_path"],
            created_at=row["created_at"],
            loan_available=bool(row["loan_available"]) if "loan_available" in keys else False,
            agent_comment=row["agent_comment"] if "agent_comment" in keys else None,
            interior_paths=json.loads(row["interior_paths"]) if "interior_paths" in keys and row["interior_paths"] else [],
        )
