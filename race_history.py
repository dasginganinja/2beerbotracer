import sqlite3
from datetime import datetime, timezone


STATUS_PENDING = "pending"
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_UNKNOWN = "unknown"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def initialize_database(db_path: str) -> None:
    with connect(db_path) as connection:
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
                foreign key (race_id) references races(id) on delete cascade
            )
            """
        )
        if _race_entries_needs_cascade_migration(connection):
            _migrate_race_entries_to_cascade(connection)
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


def _race_entries_needs_cascade_migration(connection) -> bool:
    foreign_keys = connection.execute(
        "pragma foreign_key_list(race_entries)"
    ).fetchall()
    for foreign_key in foreign_keys:
        if foreign_key["table"] == "races" and foreign_key["from"] == "race_id":
            return foreign_key["on_delete"].upper() != "CASCADE"
    return False


def _migrate_race_entries_to_cascade(connection) -> None:
    connection.commit()
    connection.execute("pragma foreign_keys = off")
    connection.execute("alter table race_entries rename to race_entries_old")
    connection.execute(
        """
        create table race_entries (
            id integer primary key,
            race_id integer not null,
            position integer not null,
            display_number integer not null,
            name text not null,
            normalized_name text not null,
            foreign key (race_id) references races(id) on delete cascade
        )
        """
    )
    connection.execute(
        """
        insert into race_entries (
            id,
            race_id,
            position,
            display_number,
            name,
            normalized_name
        )
        select
            id,
            race_id,
            position,
            display_number,
            name,
            normalized_name
        from race_entries_old
        """
    )
    connection.execute("drop table race_entries_old")
    connection.commit()
    connection.execute("pragma foreign_keys = on")


def display_car_number(position: int) -> int:
    if position == 29:
        return 69
    return position


def normalize_name(name: str) -> str:
    return name.strip().lstrip("@").lower()


def connect(db_path: str):
    connection = sqlite3.connect(db_path)
    connection.execute("pragma foreign_keys = on")
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


def get_latest_pending_race(db_path: str) -> dict | None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        row = connection.execute(
            """
            select *
            from races
            where status = ?
            order by id desc
            limit 1
            """,
            (STATUS_PENDING,),
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


def find_entry_by_display_number(
    entries: list[dict], display_number: int
) -> dict | None:
    for entry in entries:
        if entry["display_number"] == display_number:
            return entry
    return None


def find_entry_by_name(entries: list[dict], search_text: str) -> dict | None:
    normalized_search = normalize_name(search_text)
    for entry in entries:
        if entry["normalized_name"] == normalized_search:
            return entry
    return None


def find_entry(entries: list[dict], query: str) -> dict | None:
    stripped_query = query.strip()
    if stripped_query.isdecimal():
        return find_entry_by_display_number(entries, int(stripped_query))
    return find_entry_by_name(entries, stripped_query)


def latest_pending_race_matches_entries(db_path: str, entries: list[str]) -> bool:
    race = get_latest_pending_race(db_path)
    if race is None:
        return False

    race_entries = get_race_entries(db_path, race["id"])
    snapshot = [entry["normalized_name"] for entry in race_entries]
    current_entries = [normalize_name(entry) for entry in entries]
    return snapshot == current_entries


def delete_race(db_path: str, race_id: int) -> None:
    initialize_database(db_path)
    with connect(db_path) as connection:
        connection.execute("delete from races where id = ?", (race_id,))


def get_racer_stats(db_path: str, name: str) -> dict:
    initialize_database(db_path)
    normalized_name = normalize_name(name)

    with connect(db_path) as connection:
        latest_entry = connection.execute(
            """
            select name
            from race_entries
            where normalized_name = ?
            order by race_id desc, id desc
            limit 1
            """,
            (normalized_name,),
        ).fetchone()
        total_races = connection.execute(
            """
            select count(*)
            from race_entries
            where normalized_name = ?
            """,
            (normalized_name,),
        ).fetchone()[0]
        wins = connection.execute(
            """
            select count(*)
            from races
            join race_entries
                on race_entries.id = races.winner_entry_id
            where race_entries.normalized_name = ?
            """,
            (normalized_name,),
        ).fetchone()[0]

    display_name = latest_entry["name"] if latest_entry is not None else name
    win_percentage = round((wins / total_races) * 100, 1) if total_races else 0.0
    return {
        "name": display_name,
        "wins": wins,
        "total_races": total_races,
        "win_percentage": win_percentage,
    }


def update_race_result(
    db_path: str,
    race_id: int,
    status: str,
    winner_entry: dict | None = None,
    ended_at_utc: str | None = None,
) -> dict:
    initialize_database(db_path)
    ended_timestamp = ended_at_utc or utc_now_iso()
    updated_timestamp = utc_now_iso()
    winner_entry_id = winner_entry["id"] if winner_entry is not None else None
    winner_name = winner_entry["name"] if winner_entry is not None else None

    with connect(db_path) as connection:
        connection.execute(
            """
            update races
            set status = ?,
                winner_entry_id = ?,
                winner_name = ?,
                ended_at_utc = ?,
                updated_at_utc = ?
            where id = ?
            """,
            (
                status,
                winner_entry_id,
                winner_name,
                ended_timestamp,
                updated_timestamp,
                race_id,
            ),
        )
        row = connection.execute(
            "select * from races where id = ?",
            (race_id,),
        ).fetchone()

    race = dict(row)
    return {
        "race": race,
        "status": race["status"],
        "winner_name": race["winner_name"],
        "stats": get_racer_stats(db_path, winner_name) if winner_name else None,
    }


def complete_latest_pending_race(
    db_path: str,
    winner_query: str,
    ended_at_utc: str | None = None,
) -> dict | None:
    race = get_latest_pending_race(db_path)
    if race is None:
        return None

    entries = get_race_entries(db_path, race["id"])
    winner_entry = find_entry(entries, winner_query)
    if winner_entry is None:
        return {"error": "winner_not_found", "query": winner_query}

    return update_race_result(
        db_path,
        race["id"],
        STATUS_COMPLETED,
        winner_entry,
        ended_at_utc=ended_at_utc,
    )


def set_latest_race_result(
    db_path: str,
    result_query: str,
    ended_at_utc: str | None = None,
) -> dict | None:
    race = get_latest_race(db_path)
    if race is None:
        return None

    normalized_query = normalize_name(result_query)
    if normalized_query == STATUS_SKIPPED:
        return update_race_result(
            db_path,
            race["id"],
            STATUS_SKIPPED,
            ended_at_utc=ended_at_utc,
        )
    if normalized_query == STATUS_UNKNOWN:
        return update_race_result(
            db_path,
            race["id"],
            STATUS_UNKNOWN,
            ended_at_utc=ended_at_utc,
        )

    entries = get_race_entries(db_path, race["id"])
    winner_entry = find_entry(entries, result_query)
    if winner_entry is None:
        return {"error": "winner_not_found", "query": result_query}

    return update_race_result(
        db_path,
        race["id"],
        STATUS_COMPLETED,
        winner_entry,
        ended_at_utc=ended_at_utc,
    )


def get_leaderboard(db_path: str, limit: int = 5) -> list[dict]:
    initialize_database(db_path)
    with connect(db_path) as connection:
        rows = connection.execute(
            """
            select
                race_entries.normalized_name,
                (
                    select latest_entry.name
                    from race_entries latest_entry
                    where latest_entry.normalized_name =
                        race_entries.normalized_name
                    order by latest_entry.race_id desc, latest_entry.id desc
                    limit 1
                ) as name,
                count(*) as total_races,
                count(races.winner_entry_id) as wins
            from race_entries
            left join races
                on races.winner_entry_id = race_entries.id
            group by race_entries.normalized_name
            order by wins desc, race_entries.normalized_name asc
            limit ?
            """,
            (limit,),
        ).fetchall()

    leaderboard = []
    for row in rows:
        total_races = row["total_races"]
        wins = row["wins"]
        leaderboard.append(
            {
                "name": row["name"],
                "wins": wins,
                "total_races": total_races,
                "win_percentage": round((wins / total_races) * 100, 1)
                if total_races
                else 0.0,
            }
        )
    return leaderboard
