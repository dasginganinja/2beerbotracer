import sqlite3
from datetime import datetime, timezone


STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_UNKNOWN = "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_database(db_path: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            create table if not exists races (
                id integer primary key,
                started_at_utc text not null,
                ended_at_utc text,
                entries_opened_at_utc text,
                entries_closed_at_utc text,
                status text not null,
                winner_entry_id integer,
                winner_name text,
                created_by text,
                updated_at_utc text not null
            )
            """
        )
        connection.execute(
            """
            create table if not exists race_entries (
                id integer primary key,
                race_id integer not null,
                position integer not null,
                display_number integer not null,
                name text not null,
                normalized_name text not null,
                foreign key (race_id) references races(id)
            )
            """
        )
        connection.execute(
            "create index if not exists idx_races_status on races(status)"
        )
        connection.execute(
            "create index if not exists idx_race_entries_race_id "
            "on race_entries(race_id)"
        )
        connection.execute(
            "create index if not exists idx_race_entries_normalized_name "
            "on race_entries(normalized_name)"
        )


def display_car_number(position: int) -> int:
    if position == 29:
        return 69
    return position


def normalize_name(name: str) -> str:
    return name.strip().lstrip("@").lower()


def connect(db_path: str):
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def start_race(
    db_path: str,
    entries: list[str],
    started_at_utc: str | None = None,
    entries_opened_at_utc: str | None = None,
    entries_closed_at_utc: str | None = None,
    created_by: str | None = None,
) -> int:
    initialize_database(db_path)
    timestamp = started_at_utc or utc_now_iso()

    with connect(db_path) as connection:
        cursor = connection.execute(
            """
            insert into races (
                started_at_utc,
                ended_at_utc,
                entries_opened_at_utc,
                entries_closed_at_utc,
                status,
                winner_entry_id,
                winner_name,
                created_by,
                updated_at_utc
            )
            values (?, null, ?, ?, ?, null, null, ?, ?)
            """,
            (
                timestamp,
                entries_opened_at_utc,
                entries_closed_at_utc,
                STATUS_PENDING,
                created_by,
                timestamp,
            ),
        )
        race_id = int(cursor.lastrowid)
        connection.executemany(
            """
            insert into race_entries (
                race_id,
                position,
                display_number,
                name,
                normalized_name
            )
            values (?, ?, ?, ?, ?)
            """,
            [
                (
                    race_id,
                    position,
                    display_car_number(position),
                    name,
                    normalize_name(name),
                )
                for position, name in enumerate(entries, start=1)
            ],
        )

    return race_id


def get_latest_race(db_path: str) -> dict | None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            """
            select *
            from races
            order by id desc
            limit 1
            """
        ).fetchone()
    return dict(row) if row is not None else None


def get_race_entries(db_path: str, race_id: int) -> list[dict]:
    initialize_database(db_path)
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            select *
            from race_entries
            where race_id = ?
            order by position
            """,
            (race_id,),
        ).fetchall()
    return [dict(row) for row in rows]
