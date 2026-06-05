import sqlite3

import pytest

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


def test_delete_race_api_cascades_to_race_entries(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_id = race_history.start_race(str(db_path), entries=["racer_one"])

    race_history.delete_race(str(db_path), race_id)

    assert race_history.get_latest_race(str(db_path)) is None
    assert race_history.get_race_entries(str(db_path), race_id) == []


def test_connect_context_manager_closes_connection(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), entries=["racer_one"])
    race_history.get_latest_race(str(db_path))

    with race_history.connect(str(db_path)) as connection:
        connection.execute("select 1")

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("select 1")

    db_path.unlink()


def test_initialize_database_migrates_old_race_entries_fk_to_cascade(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            create table races (
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
            create table race_entries (
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
        race_id = connection.execute(
            """
            insert into races (
                started_at_utc,
                status,
                updated_at_utc
            )
            values (?, ?, ?)
            """,
            (
                "2026-06-04T20:00:00+00:00",
                race_history.STATUS_PENDING,
                "2026-06-04T20:00:00+00:00",
            ),
        ).lastrowid
        connection.execute(
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
            (race_id, 1, 1, "racer_one", "racer_one"),
        )

    race_history.initialize_database(str(db_path))

    with race_history.connect(str(db_path)) as connection:
        connection.execute("delete from races where id = ?", (race_id,))
        entry_count = connection.execute(
            "select count(*) from race_entries where race_id = ?",
            (race_id,),
        ).fetchone()[0]

    assert entry_count == 0


def test_complete_latest_pending_race_records_winner_and_stats(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(
        str(db_path),
        ["RacerOne", "RacerTwo"],
        started_at_utc="2026-06-04T20:00:00+00:00",
    )

    result = race_history.complete_latest_pending_race(
        str(db_path),
        winner_query="2",
        ended_at_utc="2026-06-04T20:05:00+00:00",
    )

    assert result["status"] == race_history.STATUS_COMPLETED
    assert result["winner_name"] == "RacerTwo"
    assert result["stats"] == {
        "name": "RacerTwo",
        "wins": 1,
        "total_races": 1,
        "win_percentage": 100.0,
    }


def test_set_latest_race_winner_can_correct_completed_race(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne", "RacerTwo"])
    race_history.complete_latest_pending_race(str(db_path), "RacerOne")

    result = race_history.set_latest_race_result(str(db_path), "RacerTwo")

    assert result["status"] == race_history.STATUS_COMPLETED
    assert result["winner_name"] == "RacerTwo"
    assert race_history.get_racer_stats(str(db_path), "RacerOne")["wins"] == 0
    assert race_history.get_racer_stats(str(db_path), "RacerTwo")["wins"] == 1


def test_set_latest_race_result_supports_skipped_and_unknown(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne"])

    skipped = race_history.set_latest_race_result(str(db_path), "skipped")
    unknown = race_history.set_latest_race_result(str(db_path), "unknown")

    assert skipped["status"] == race_history.STATUS_SKIPPED
    assert skipped["winner_name"] is None
    assert unknown["status"] == race_history.STATUS_UNKNOWN
    assert unknown["winner_name"] is None
    assert race_history.get_racer_stats(str(db_path), "RacerOne") == {
        "name": "RacerOne",
        "wins": 0,
        "total_races": 1,
        "win_percentage": 0.0,
    }


def test_leaderboard_orders_by_wins_then_name(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    for winner in ["Beta", "Alpha", "Beta"]:
        race_history.start_race(str(db_path), ["Alpha", "Beta"])
        race_history.complete_latest_pending_race(str(db_path), winner)

    assert race_history.get_leaderboard(str(db_path), limit=5) == [
        {"name": "Beta", "wins": 2, "total_races": 3, "win_percentage": 66.7},
        {"name": "Alpha", "wins": 1, "total_races": 3, "win_percentage": 33.3},
    ]


def test_get_car_stats_reports_display_number_performance(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["Alice", "Bob", "Cara"])
    race_history.complete_latest_pending_race(str(db_path), "Bob")
    race_history.start_race(str(db_path), ["Dana", "Eli", "Fay"])
    race_history.complete_latest_pending_race(str(db_path), "Eli")
    race_history.start_race(str(db_path), ["Gus", "Hal", "Ivy"])
    race_history.complete_latest_pending_race(str(db_path), "Ivy")

    assert race_history.get_car_stats(str(db_path), 2) == {
        "display_number": 2,
        "wins": 2,
        "total_races": 3,
        "win_percentage": 66.7,
        "best_driver": "Bob",
        "best_driver_wins": 1,
        "last_win": "Eli",
    }


def test_get_car_stats_reports_appearances_without_wins(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["Alice", "Bob"])
    race_history.complete_latest_pending_race(str(db_path), "Alice")

    assert race_history.get_car_stats(str(db_path), 2) == {
        "display_number": 2,
        "wins": 0,
        "total_races": 1,
        "win_percentage": 0.0,
        "best_driver": None,
        "best_driver_wins": 0,
        "last_win": None,
    }


def test_get_car_stats_returns_none_for_unrecorded_car(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["Alice"])

    assert race_history.get_car_stats(str(db_path), 7) is None


def test_get_car_leaderboard_ranks_by_wins_rate_and_number(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["A1", "B1", "C1"])
    race_history.complete_latest_pending_race(str(db_path), "B1")
    race_history.start_race(str(db_path), ["A2", "B2", "C2"])
    race_history.complete_latest_pending_race(str(db_path), "B2")
    race_history.start_race(str(db_path), ["A3", "B3", "C3"])
    race_history.complete_latest_pending_race(str(db_path), "C3")

    assert race_history.get_car_leaderboard(str(db_path), limit=2) == [
        {
            "display_number": 2,
            "wins": 2,
            "total_races": 3,
            "win_percentage": 66.7,
        },
        {
            "display_number": 3,
            "wins": 1,
            "total_races": 3,
            "win_percentage": 33.3,
        },
    ]


def test_stats_and_leaderboard_ignore_residual_winner_for_unknown_race(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne"])
    race_history.complete_latest_pending_race(str(db_path), "RacerOne")

    with race_history.connect(str(db_path)) as connection:
        connection.execute(
            """
            update races
            set status = ?
            """,
            (race_history.STATUS_UNKNOWN,),
        )

    assert race_history.get_racer_stats(str(db_path), "RacerOne")["wins"] == 0
    assert race_history.get_leaderboard(str(db_path)) == []


def test_stats_and_leaderboard_count_duplicate_normalized_entries_once(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne", "racerone"])
    race_history.complete_latest_pending_race(str(db_path), "RacerOne")

    assert race_history.get_racer_stats(str(db_path), "racerone") == {
        "name": "racerone",
        "wins": 1,
        "total_races": 1,
        "win_percentage": 100.0,
    }
    assert race_history.get_leaderboard(str(db_path))[0] == {
        "name": "racerone",
        "wins": 1,
        "total_races": 1,
        "win_percentage": 100.0,
    }


def test_pending_race_blocks_next_start_when_snapshot_differs(tmp_path):
    db_path = tmp_path / "race-history.sqlite3"
    race_history.start_race(str(db_path), ["RacerOne"])

    assert race_history.latest_pending_race_matches_entries(
        str(db_path), ["RacerTwo"]
    ) is False
    assert race_history.latest_pending_race_matches_entries(
        str(db_path), ["RacerOne"]
    ) is True
