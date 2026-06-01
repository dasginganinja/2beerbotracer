import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOT_SOURCE = PROJECT_ROOT / "trackracerbot.py"


def parse_bot_source():
    return ast.parse(BOT_SOURCE.read_text(encoding="utf-8"))


class TrackRacerBotStructureTests(unittest.TestCase):
    def test_trackracerbot_startup_is_protected_by_main_guard(self):
        tree = parse_bot_source()

        guarded_calls = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
                and len(test.ops) == 1
                and isinstance(test.ops[0], ast.Eq)
                and len(test.comparators) == 1
                and isinstance(test.comparators[0], ast.Constant)
                and test.comparators[0].value == "__main__"
            ):
                guarded_calls.extend(node.body)

        self.assertTrue(
            any(
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "main"
                for node in guarded_calls
            )
        )


if __name__ == "__main__":
    unittest.main()
