import sqlite3

import race_history


def test_initialize_database_creates_tables(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"

    race_history.initialize_database(str(db_path))

    with sqlite3.connect(db_path) as connection:
        table_names = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table'"
            )
        }

    assert {"races", "race_entries"} <= table_names


def test_start_race_stores_entry_snapshot_with_display_numbers(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.initialize_database(str(db_path))

    race_id = race_history.start_race(
        str(db_path),
        entries=["racer_one"] + [f"racer_{index}" for index in range(2, 30)],
        started_at_utc="2026-06-04T20:00:00+00:00",
        entries_opened_at_utc="2026-06-04T19:50:00+00:00",
        entries_closed_at_utc="2026-06-04T20:00:00+00:00",
        created_by="example_mod",
    )

    race = race_history.get_latest_race(str(db_path))
    entries = race_history.get_race_entries(str(db_path), race_id)

    assert race["id"] == race_id
    assert race["status"] == race_history.STATUS_PENDING
    assert race["started_at_utc"] == "2026-06-04T20:00:00+00:00"
    assert race["entries_opened_at_utc"] == "2026-06-04T19:50:00+00:00"
    assert race["entries_closed_at_utc"] == "2026-06-04T20:00:00+00:00"
    assert race["created_by"] == "example_mod"
    assert entries[0]["name"] == "racer_one"
    assert entries[0]["position"] == 1
    assert entries[0]["display_number"] == 1
    assert entries[28]["position"] == 29
    assert entries[28]["display_number"] == 69


def test_deleting_race_cascades_to_race_entries(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.initialize_database(str(db_path))
    race_id = race_history.start_race(str(db_path), entries=["racer_one"])

    with race_history.connect(str(db_path)) as connection:
        connection.execute("delete from races where id = ?", (race_id,))
        entry_count = connection.execute(
            "select count(*) from race_entries where race_id = ?",
            (race_id,),
        ).fetchone()[0]

    assert entry_count == 0
