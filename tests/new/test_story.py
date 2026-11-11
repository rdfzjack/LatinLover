"""Whole game: runs from the opening to an ending without errors, the same seed repeats, and saving and loading mid-game gives the same result afterwards."""
import unittest
from sim import film
from sim.month import Game, trace_line
from sim.story import Story, SimpleAgent, fit_plan, new_game, run
from tests.new.helpers import D

PLANS = [
    ['class_acting', 'job_dock', 'rest_home'],
    ['class_boxing', 'job_bar', 'rest_outing@place_dock'],
    ['class_tutor', 'job_news', 'rest_outing@place_downtown'],
    ['class_dance', 'job_waiter', 'rest_outing@place_seaside'],
    ['job_assistant', 'job_studio', 'rest_outing@place_studio'],
]


class TestStory(unittest.TestCase):
    def test_full_games(self):
        for k, plan in enumerate(PLANS):
            for seed in (1, 2):
                with self.subTest(plan=plan, seed=seed):
                    origin = (k % 5, seed % 4, k % 6)
                    lines, g = run(seed, origin, plan)
                    st = g.st
                    self.assertTrue(st.finished)
                    self.assertIsNotNone(st.story['ending'])
                    self.assertEqual(st.ended, st.story['ending']['ending'])
                    if st.ended != 'end_collapse':
                        self.assertEqual(len(lines), 48)
                        self.assertIn('total', st.story['ending'])
                    self.assertGreater(len(film.films(st)), 0)

    def test_deterministic(self):
        a, ga = run(5, (1, 2, 3), PLANS[3])
        b, gb = run(5, (1, 2, 3), PLANS[3])
        self.assertEqual(a, b)
        self.assertEqual(ga.st.dumps(), gb.st.dumps())

    def test_save_restore_midgame(self):
        plan = PLANS[2]
        ref, gref = run(7, (2, 1, 0), plan)
        g = new_game(7, (2, 1, 0))
        lines = []
        while not g.st.finished:
            if g.st.ym == 17:
                g = Game.restore(g.save(), D, Story(SimpleAgent()))
            date = g.st.date
            g.start_month()
            g.run_month(fit_plan(g, plan))
            lines.append(trace_line(g.st, date))
        self.assertEqual(lines, ref)
        self.assertEqual(g.st.dumps(), gref.st.dumps())

    def test_films_lock_next_month(self):
        lines, g = run(1, (0, 1, 2), PLANS[0])
        for f in film.films(g.st):
            if f['status'] == 'released':
                last = f['locks'][-1][0]
                self.assertEqual(f['result']['month'], last + 2)


if __name__ == '__main__':
    unittest.main()
