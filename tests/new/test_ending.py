"""Ending resolution: every ending in endings.json has a situation that reaches it (completion standard of PLAN step 6)."""
import unittest
from sim import ending
from tests.new.helpers import D, bare

ROADS = ['tough', 'lover', 'culture', 'savvy']


def build(attr=None, skill=None, rep=None, tags=None, flags=None, favor=None, count=None):
    """Builds a situation. Attributes start from a neutral set of base values; skills are all 0; reputation is made up with rep_bonus to the given numbers (roads not mentioned are 0)."""
    st = bare()
    st.attr.update({'stamina': 100, 'education': 50, 'loyalty': 100, 'looks': 100, 'discipline': 50, 'crime': 0, 'fatigue': 0, 'fame': 0})
    st.attr.update(attr or {})
    for k in st.skill:
        st.skill[k] = 0
    st.skill.update(skill or {})
    st.tags.update(tags or {})
    st.flags.update(flags or {})
    st.favor.update(favor or {})
    st.count.update(count or {})
    want = {r: 0 for r in ROADS}
    want.update(rep or {})
    for r in ROADS:
        st.corr[r] = 0
        st.corr[r] = want[r] - st.rep(r)
    return st


def solo(road, v, **kw):
    """Only one road has reputation (the rest are 0), used for the road categories."""
    return build(rep={road: v}, **kw)


CASES = [
    # special
    ('end_underworld', dict(attr={'crime': 500, 'discipline': 0}, rep={'tough': 300, 'savvy': 200})),
    ('end_idol', dict(attr={'fame': 500, 'loyalty': 40}, flags={'berlin_invite': 1}, rep={'lover': 300})),
    # dark
    ('dark_boss', dict(attr={'discipline': 0, 'crime': 100, 'loyalty': 200}, rep={'tough': 210})),
    ('dark_thug_boss', dict(attr={'discipline': 20, 'crime': 250}, rep={'tough': 210})),
    ('dark_marry', dict(attr={'crime': 400, 'looks': 200}, skill={'speech': 70, 'negotiation': 70, 'connections': 70}, rep={'lover': 300})),
    ('dark_con', dict(attr={'crime': 400, 'looks': 150}, skill={'negotiation': 70}, rep={'savvy': 300})),
    ('dark_prison', dict(attr={'crime': 400}, rep={'culture': 300})),
    # actor (fame >= 300)
    ('act_legend', dict(attr={'fame': 300}, rep={'lover': 451})),
    ('act_lowbudget', dict(attr={'fame': 300}, rep={'lover': 381}, count={'count.lowbudget': 4}, skill={'speech': 40})),
    ('act_undefined', dict(attr={'fame': 300}, rep={'lover': 311}, skill={'speech': 40},
                           tags={'western': 1, 'romance': 1, 'arthouse': 1, 'crime': 1, 'comedy': 1, 'religious': 2})),
    ('act_voice', dict(attr={'fame': 300}, rep={'culture': 381}, skill={'speech': 80}, count={'count.talkie_count': 3})),
    ('act_lover', dict(attr={'fame': 300}, rep={'lover': 381}, skill={'speech': 40}, tags={'romance': 3, 'western': 2})),
    ('act_action', dict(attr={'fame': 300}, rep={'tough': 311}, skill={'speech': 40}, tags={'western': 2, 'war': 2})),
    ('act_character', dict(attr={'fame': 300}, rep={'savvy': 311}, skill={'speech': 40}, tags={'villain': 3})),
    ('act_art', dict(attr={'fame': 300}, rep={'culture': 381}, skill={'speech': 40}, tags={'arthouse': 2, 'tragic': 2})),
    ('act_comedy', dict(attr={'fame': 300}, rep={'savvy': 381}, skill={'speech': 40}, tags={'comedy': 2, 'noble': 1})),
    ('act_silent', dict(attr={'fame': 300}, rep={'lover': 381}, skill={'speech': 20})),   # speech <30; ranked after the tag families
    ('act_second', dict(attr={'fame': 300}, rep={'lover': 300}, skill={'speech': 40})),
    ('act_fallback', dict(attr={'fame': 300}, rep={'lover': 381}, skill={'speech': 40})),
    # all-round (spread of the four roads <50)
    ('all_studio', dict(rep={'tough': 460, 'lover': 455, 'culture': 451, 'savvy': 470})),
    ('all_director', dict(rep={'tough': 300, 'lover': 311, 'culture': 300, 'savvy': 300})),
    ('all_job_formal', dict(rep={'tough': 220, 'lover': 211, 'culture': 200, 'savvy': 200}, count={'job_periods.job_dock': 5})),
    ('all_job_temp', dict(rep={'tough': 100, 'lover': 90, 'culture': 80, 'savvy': 100}, count={'job_periods.job_bar': 6})),
    ('all_naples', dict(rep={'tough': 100, 'lover': 90, 'culture': 80, 'savvy': 100}, count={'job_periods.job_bar': 4})),
    # tough
    ('tough_adventurer', dict(rep={'tough': 381}, attr={'discipline': 30})),
    ('tough_stunt', dict(rep={'tough': 311}, attr={'loyalty': 150, 'discipline': 30})),
    ('tough_rider', dict(rep={'tough': 311}, attr={'loyalty': 149, 'discipline': 30})),
    ('tough_gym', dict(rep={'tough': 211}, attr={'discipline': 30})),
    ('tough_double', dict(rep={'tough': 100}, attr={'discipline': 50})),
    ('tough_thug', dict(rep={'tough': 100}, attr={'discipline': 49})),
    # lover
    ('lover_darling', dict(rep={'lover': 381}, attr={'looks': 500})),
    ('lover_salon', dict(rep={'lover': 381}, attr={'looks': 300, 'education': 300})),
    ('lover_widow', dict(rep={'lover': 311}, attr={'looks': 300, 'education': 200})),
    ('lover_dance_teacher', dict(rep={'lover': 211}, attr={'looks': 100, 'education': 100})),
    ('lover_dance_hall', dict(rep={'lover': 211}, attr={'looks': 100, 'education': 50})),
    ('lover_pinup', dict(rep={'lover': 100}, attr={'looks': 150})),
    ('lover_gigolo', dict(rep={'lover': 100}, attr={'looks': 149})),
    # culture
    ('cult_writer', dict(rep={'culture': 451}, skill={'writing': 60, 'taste': 50}, attr={'discipline': 50})),
    ('cult_photog', dict(rep={'culture': 381}, skill={'writing': 40, 'taste': 50}, attr={'discipline': 50})),
    ('cult_screenwriter', dict(rep={'culture': 311}, attr={'discipline': 50})),
    ('cult_tabloid', dict(rep={'culture': 381}, attr={'discipline': 49})),
    ('cult_editor', dict(rep={'culture': 211})),
    ('cult_letter', dict(rep={'culture': 100}, attr={'loyalty': 100})),
    ('cult_street_photo', dict(rep={'culture': 100}, attr={'loyalty': 99})),
    # savvy
    ('biz_producer', dict(rep={'savvy': 381}, favor={'studio_boss': 80})),
    ('biz_agent', dict(rep={'savvy': 381})),
    ('biz_dealer', dict(rep={'savvy': 311}, skill={'negotiation': 20, 'connections': 30, 'business': 50})),
    ('biz_broker', dict(rep={'savvy': 311}, skill={'negotiation': 60, 'connections': 30, 'business': 50})),
    ('biz_boss', dict(rep={'savvy': 211})),
    ('biz_sales', dict(rep={'savvy': 100})),
]


class TestEndings(unittest.TestCase):
    def test_every_ending_has_a_case(self):
        t = D.t['endings']
        ids = {e['id'] for e in t['endings'] + t['special']}
        self.assertEqual(ids, {c[0] for c in CASES})

    def test_cases(self):
        for eid, kw in CASES:
            with self.subTest(eid):
                st = build(**kw)
                res = ending.judge(st)
                self.assertEqual(res['ending'], eid)
                self.assertEqual(st.ended, eid)

    def test_collapse(self):
        st = build(rep={'lover': 300})
        st.ended = 'end_collapse'
        self.assertEqual(ending.judge(st)['ending'], 'end_collapse')

    def test_tier_and_vars(self):
        st = build(rep={'lover': 420})
        self.assertEqual(ending.tier(st), 'A')
        st.tags.update({'western': 2, 'costume': 1, 'romance': 3})
        self.assertEqual(ending.biggest_family(st), 'lover_family')      # 3:3 ties follow the table order, lover family first
        st.tags['western'] = 5
        self.assertEqual(ending.biggest_family(st), 'action_family')
        st.tags.clear()
        self.assertIsNone(ending.biggest_family(st))

    def test_home_and_score(self):
        st = build(rep={'lover': 381}, attr={'looks': 200, 'discipline': 100}, favor={'sil': 100, 'actress': 95})
        res = ending.judge(st)
        self.assertEqual(res['destiny'], {'class': 'special', 'target': 'sil', 'good': True})
        # When both Sil and actress qualify the one with the higher favor wins
        st = build(rep={'lover': 381}, attr={'looks': 200, 'discipline': 100, 'loyalty': 200}, favor={'sil': 100, 'actress': 95})
        self.assertEqual(ending.judge(st)['destiny']['target'], 'sil')
        # ordinary destiny: discipline >= 30 mode one, looks >= 200
        st = build(rep={'lover': 381}, attr={'looks': 250, 'discipline': 40})
        res = ending.judge(st)
        self.assertEqual(res['destiny'], {'class': 'ordinary', 'mode': 1, 'good': True})
        # total = (stamina+education+loyalty+looks+discipline+fame)/6 - crime + ending_score(A 400) + character_score(default plum -10) + ordinary_good 40
        self.assertEqual(res['total'], (100 + 50 + 100 + 250 + 40 + 0) // 6 - 0 + 400 - 10 + 40)

    def test_idol_drops_sil(self):
        st = build(attr={'fame': 500, 'loyalty': 40, 'looks': 200, 'discipline': 100}, flags={'berlin_invite': 1},
                   rep={'lover': 300}, favor={'sil': 100})
        res = ending.judge(st)
        self.assertEqual(res['ending'], 'end_idol')
        self.assertEqual(res['destiny']['class'], 'ordinary')


if __name__ == '__main__':
    unittest.main()
