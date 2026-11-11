"""结局判定：endings.json 里每个结局都有一条能走到它的局面（PLAN 第 6 步的完成标准）。"""
import unittest
from sim import ending
from tests.new.helpers import D, bare

ROADS = ['硬汉', '情人', '文化', '手腕']


def build(attr=None, skill=None, rep=None, tags=None, flags=None, favor=None, count=None):
    """造一个局面。属性先取一组中性的底值；技能全 0；声望用修正值凑成指定数（没写的路为 0）。"""
    st = bare()
    st.attr.update({'体力': 100, '教育': 50, '义气': 100, '相貌': 100, '自律': 50, '犯罪': 0, '疲劳': 0, '名气': 0})
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
    """只有一条路有声望（其余 0），用于各路大类。"""
    return build(rep={road: v}, **kw)


CASES = [
    # 特殊
    ('end_underworld', dict(attr={'犯罪': 500, '自律': 0}, rep={'硬汉': 300, '手腕': 200})),
    ('end_idol', dict(attr={'名气': 500, '义气': 40}, flags={'柏林邀约': 1}, rep={'情人': 300})),
    # 黑暗
    ('dark_boss', dict(attr={'自律': 0, '犯罪': 100, '义气': 200}, rep={'硬汉': 210})),
    ('dark_thug_boss', dict(attr={'自律': 20, '犯罪': 250}, rep={'硬汉': 210})),
    ('dark_marry', dict(attr={'犯罪': 400, '相貌': 200}, skill={'谈吐': 70, '谈判': 70, '人脉': 70}, rep={'情人': 300})),
    ('dark_con', dict(attr={'犯罪': 400, '相貌': 150}, skill={'谈判': 70}, rep={'手腕': 300})),
    ('dark_prison', dict(attr={'犯罪': 400}, rep={'文化': 300})),
    # 演员（名气 ≥300）
    ('act_legend', dict(attr={'名气': 300}, rep={'情人': 421})),
    ('act_lowbudget', dict(attr={'名气': 300}, rep={'情人': 381}, count={'计数.低成本': 4}, skill={'谈吐': 40})),
    ('act_undefined', dict(attr={'名气': 300}, rep={'情人': 311}, skill={'谈吐': 40},
                           tags={'西部': 1, '浪漫': 1, '文艺': 1, '犯罪': 1, '喜剧': 1, '宗教': 2})),
    ('act_voice', dict(attr={'名气': 300}, rep={'文化': 381}, skill={'谈吐': 80}, count={'计数.有声片部数': 3})),
    ('act_lover', dict(attr={'名气': 300}, rep={'情人': 381}, skill={'谈吐': 40}, tags={'浪漫': 3, '西部': 2})),
    ('act_action', dict(attr={'名气': 300}, rep={'硬汉': 311}, skill={'谈吐': 40}, tags={'西部': 2, '战争': 2})),
    ('act_character', dict(attr={'名气': 300}, rep={'手腕': 311}, skill={'谈吐': 40}, tags={'反派': 3})),
    ('act_art', dict(attr={'名气': 300}, rep={'文化': 381}, skill={'谈吐': 40}, tags={'文艺': 2, '悲情': 2})),
    ('act_comedy', dict(attr={'名气': 300}, rep={'手腕': 381}, skill={'谈吐': 40}, tags={'喜剧': 2, '贵族': 1})),
    ('act_silent', dict(attr={'名气': 300}, rep={'情人': 381}, skill={'谈吐': 20})),   # 谈吐 <30；排在各标签族之后
    ('act_second', dict(attr={'名气': 300}, rep={'情人': 300}, skill={'谈吐': 40})),
    ('act_fallback', dict(attr={'名气': 300}, rep={'情人': 381}, skill={'谈吐': 40})),
    # 万能（四路极差 <50）
    ('all_studio', dict(rep={'硬汉': 430, '情人': 425, '文化': 421, '手腕': 440})),
    ('all_director', dict(rep={'硬汉': 300, '情人': 311, '文化': 300, '手腕': 300})),
    ('all_job_formal', dict(rep={'硬汉': 220, '情人': 211, '文化': 200, '手腕': 200}, count={'成功期数.job_dock': 5})),
    ('all_job_temp', dict(rep={'硬汉': 100, '情人': 90, '文化': 80, '手腕': 100}, count={'成功期数.job_bar': 6})),
    ('all_naples', dict(rep={'硬汉': 100, '情人': 90, '文化': 80, '手腕': 100}, count={'成功期数.job_bar': 4})),
    # 硬汉
    ('tough_adventurer', dict(rep={'硬汉': 381}, attr={'自律': 30})),
    ('tough_stunt', dict(rep={'硬汉': 311}, attr={'义气': 150, '自律': 30})),
    ('tough_rider', dict(rep={'硬汉': 311}, attr={'义气': 149, '自律': 30})),
    ('tough_gym', dict(rep={'硬汉': 211}, attr={'自律': 30})),
    ('tough_double', dict(rep={'硬汉': 100}, attr={'自律': 50})),
    ('tough_thug', dict(rep={'硬汉': 100}, attr={'自律': 49})),
    # 情人
    ('lover_darling', dict(rep={'情人': 381}, attr={'相貌': 500})),
    ('lover_salon', dict(rep={'情人': 381}, attr={'相貌': 300, '教育': 300})),
    ('lover_widow', dict(rep={'情人': 311}, attr={'相貌': 300, '教育': 200})),
    ('lover_dance_teacher', dict(rep={'情人': 211}, attr={'相貌': 100, '教育': 100})),
    ('lover_dance_hall', dict(rep={'情人': 211}, attr={'相貌': 100, '教育': 50})),
    ('lover_pinup', dict(rep={'情人': 100}, attr={'相貌': 150})),
    ('lover_gigolo', dict(rep={'情人': 100}, attr={'相貌': 149})),
    # 文化
    ('cult_writer', dict(rep={'文化': 421}, skill={'创作': 60, '审美': 50}, attr={'自律': 50})),
    ('cult_photog', dict(rep={'文化': 381}, skill={'创作': 40, '审美': 50}, attr={'自律': 50})),
    ('cult_screenwriter', dict(rep={'文化': 311}, attr={'自律': 50})),
    ('cult_tabloid', dict(rep={'文化': 381}, attr={'自律': 49})),
    ('cult_editor', dict(rep={'文化': 211})),
    ('cult_letter', dict(rep={'文化': 100}, attr={'义气': 100})),
    ('cult_street_photo', dict(rep={'文化': 100}, attr={'义气': 99})),
    # 手腕
    ('biz_producer', dict(rep={'手腕': 381}, favor={'片厂老板': 80})),
    ('biz_agent', dict(rep={'手腕': 381})),
    ('biz_dealer', dict(rep={'手腕': 311}, skill={'谈判': 20, '人脉': 30, '生意': 50})),
    ('biz_broker', dict(rep={'手腕': 311}, skill={'谈判': 60, '人脉': 30, '生意': 50})),
    ('biz_boss', dict(rep={'手腕': 211})),
    ('biz_sales', dict(rep={'手腕': 100})),
]


class TestEndings(unittest.TestCase):
    def test_every_ending_has_a_case(self):
        t = D.t['endings']
        ids = {e['id'] for e in t['结局'] + t['特殊']}
        self.assertEqual(ids, {c[0] for c in CASES})

    def test_cases(self):
        for eid, kw in CASES:
            with self.subTest(eid):
                st = build(**kw)
                res = ending.judge(st)
                self.assertEqual(res['结局'], eid)
                self.assertEqual(st.ended, eid)

    def test_collapse(self):
        st = build(rep={'情人': 300})
        st.ended = 'end_collapse'
        self.assertEqual(ending.judge(st)['结局'], 'end_collapse')

    def test_tier_and_vars(self):
        st = build(rep={'情人': 420})
        self.assertEqual(ending.tier(st), 'A')
        st.tags.update({'西部': 2, '古装': 1, '浪漫': 3})
        self.assertEqual(ending.biggest_family(st), '情人系')      # 3:3 并列按表的顺序，情人系在前
        st.tags['西部'] = 5
        self.assertEqual(ending.biggest_family(st), '动作系')
        st.tags.clear()
        self.assertIsNone(ending.biggest_family(st))

    def test_home_and_score(self):
        st = build(rep={'情人': 381}, attr={'相貌': 200, '自律': 100}, favor={'Sil': 100, '女明星': 95})
        res = ending.judge(st)
        self.assertEqual(res['归宿'], {'类': '特殊', '对象': 'Sil', '好': True})
        # Sil 和女明星都满足时取好感高的
        st = build(rep={'情人': 381}, attr={'相貌': 200, '自律': 100, '义气': 200}, favor={'Sil': 100, '女明星': 95})
        self.assertEqual(ending.judge(st)['归宿']['对象'], 'Sil')
        # 普通归宿：自律 ≥30 模式一，看相貌 ≥200
        st = build(rep={'情人': 381}, attr={'相貌': 250, '自律': 40})
        res = ending.judge(st)
        self.assertEqual(res['归宿'], {'类': '普通', '模式': 1, '好': True})
        # 总分 = (体力+教育+义气+相貌+自律+名气)/6 − 犯罪 + 结局分(A 400) + 品性分(默认梅 −10) + 普通好归宿 40
        self.assertEqual(res['总分'], (100 + 50 + 100 + 250 + 40 + 0) // 6 - 0 + 400 - 10 + 40)

    def test_idol_drops_sil(self):
        st = build(attr={'名气': 500, '义气': 40, '相貌': 200, '自律': 100}, flags={'柏林邀约': 1},
                   rep={'情人': 300}, favor={'Sil': 100})
        res = ending.judge(st)
        self.assertEqual(res['结局'], 'end_idol')
        self.assertEqual(res['归宿']['类'], '普通')


if __name__ == '__main__':
    unittest.main()
