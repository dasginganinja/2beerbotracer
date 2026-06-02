import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "update_widget_ip.py"
WIDGET_FILES = ("entries-widget-1col.html", "entries-widget.html")
TEST_HOST = "example.com"


def test_widget_ip_export_writes_generated_files_without_changing_sources(tmp_path):
    source_dir = tmp_path / "sources"
    output_dir = tmp_path / "exports"
    source_dir.mkdir()

    source_files = []
    for filename in WIDGET_FILES:
        source_path = source_dir / filename
        source_path.write_text((REPO_ROOT / filename).read_text(encoding="utf-8"), encoding="utf-8")
        source_files.append(source_path)

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--ip",
            TEST_HOST,
            "--output-dir",
            str(output_dir),
            *[str(path) for path in source_files],
        ],
        check=True,
        cwd=REPO_ROOT,
    )

    for source_path in source_files:
        source_text = source_path.read_text(encoding="utf-8")
        export_text = (output_dir / source_path.name).read_text(encoding="utf-8")

        assert "ws://localhost:64209" in source_text
        assert TEST_HOST not in source_text
        assert f"ws://{TEST_HOST}:64209" in export_text
        assert "ws://localhost:64209" not in export_text
