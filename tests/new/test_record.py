"""Step 12 recordings (tools/record_game.py): replaying a recorded bot game gives the same game, extras included."""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'tools'))
import record_game as R  # noqa: E402
from tests.new.helpers import D  # noqa: E402


class TestRecord(unittest.TestCase):
    def test_replay_identical(self):
        for name, seed, extras in (('only_lover', 3, False), ('crime_line', 1, True), ('random_pick', 9, True)):
            with self.subTest(bot=name, seed=seed, extras=extras):
                rec, lines, _ = R.record(name, seed, extras, D)
                self.assertEqual(R.replay(json.loads(R.js(rec)), D), lines)
                self.assertTrue(lines[-5].startswith('ending '))

    def test_wrong_answer_is_reported(self):
        rec, _, _ = R.record('only_tough', 2, False, D)
        rec['answers'] = rec['answers'][:-1]
        self.assertTrue(R.replay(rec, D)[-1].startswith('replay error'))


if __name__ == '__main__':
    unittest.main()
