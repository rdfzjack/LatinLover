"""把第 6 步的模块接到月流程上：Story 是 month.Hooks 的实现，Agent 是玩家（界面或机器人）要回答的问题。

用法：
    from sim.story import Story, SimpleAgent, new_game
    g = new_game(seed=1, origin=(0, 1, 2), agent=SimpleAgent())
    while not g.st.finished:
        g.start_month()                  # 生活费、选片板（agent 报名、出牌）、agent.month_start
        g.run_month(plan)                # 三旬日程；被拍摄锁定的旬不看 plan
    g.st.story['结局']

命令行：python3 -m sim.story --seed 1 --origin 0,1,2 --plan class_acting,job_dock,rest_home
每月一行对账（同 sim.month），最后一行是结局。
"""
import argparse

from . import audition, board, ending, events, film, rules, schedule
from .data import load
from .month import Game, Hooks, trace_line


class Agent(audition.Player):
    """玩家要做的决定。界面和第 7 步的机器人实现这些方法；默认实现见 SimpleAgent。"""

    def pick_role(self, st, b, ok):
        """选片板：从可报名的下标 ok 里选一个去试镜，None 表示不试了。b = st.story['板']。"""
        raise NotImplementedError

    def accept_support(self, st, role):
        """惜败时接不接同片配角。"""
        raise NotImplementedError

    def go_personally(self, st, role):
        """拿到可以亲自上的角色时，要不要亲自上。"""
        raise NotImplementedError

    def option(self, st, ev, avail):
        """事件选项：avail 是能选的选项下标，返回其中一个。"""
        raise NotImplementedError

    def annual(self, st, opts):
        """年度大事：返回场合 id，None 表示休息。"""
        raise NotImplementedError

    def family(self, st):
        """片厂老板支持转型：返回戏路族名（endings.json 的 标签族）。"""
        raise NotImplementedError

    def suppress(self, st, kind):
        """丑闻要不要压下：kind 为 '免费' 或 '花钱'（200）。"""
        raise NotImplementedError

    def month_start(self, story, st):
        """月初的自由操作：story.write_script / send_detox / leak_news，街道、股票等（不占日程）。"""


class SimpleAgent(Agent):
    """最简单的玩家，测试和对账用：
    组牌 主色（等级最高）3 张 + 等级第二高的颜色 2 张；出牌用逻辑流随机；
    报名能报的最高档里第一个；接配角；能亲自上就上；事件选第一个能选的选项；
    年度大事参加声望最高的那条路；转型选第一个族；能压丑闻就压；月初不做别的事。"""

    def deck(self, st, ctx):
        lv = ctx['等级']
        order = sorted(range(4), key=lambda c: (-lv[c], c))
        return [order[0]] * 3 + [order[1]] * 2

    def play(self, st, ctx):
        return st.rng.logic.below(len(ctx['手牌']))

    def pick_role(self, st, b, ok):
        return max(ok, key=lambda i: (board.RANK[b['角色'][i]['档次']], -i))

    def accept_support(self, st, role):
        return True

    def go_personally(self, st, role):
        return True

    def option(self, st, ev, avail):
        return avail[0]

    def annual(self, st, opts):
        b = st.bonus()
        best = max(opts, key=lambda x: (st.rep(x['路'], b), -opts.index(x)))
        return best['id']

    def family(self, st):
        return next(iter(st.d.tag_families))

    def suppress(self, st, kind):
        return True


class Story(Hooks):
    def __init__(self, agent=None):
        self.agent = agent or SimpleAgent()
        self.cur_period = 0
        self.log = []          # 本局触发过的事件（不进存档）
        self.boards = []       # 每块板的试镜结果（不进存档）
        self.annuals = []

    # ---------- 月初 ----------
    def board(self, st):
        board.make(st)
        self.boards.append({'月': st.date, '试镜': board.run(st, self.agent)})

    def month_start(self, st):
        self.agent.month_start(self, st)

    # 月初的操作（玩家调用）
    def write_script(self, st, kind, color=None):
        board.write_script(st, kind, color)

    def send_detox(self, st):
        """送去戒：药瘾阶段 ≥2 时可选，当月月末触发戒断。"""
        if st.drug < 2:
            raise ValueError('药瘾阶段不到 2')
        st.flags['送去戒'] = 1

    def leak_news(self, st):
        """报馆线好感 80：每年可放一条消息，名气 +10%，算曝光。"""
        y = st.ym // 12 + 1
        if not st.flags.get('放消息') or st.story['放消息年'] == y:
            raise ValueError('现在不能放消息')
        st.story['放消息年'] = y
        events.fame_pct(st, 10)
        st.exposed = 1

    # ---------- 三旬 ----------
    def locked(self, st, i):
        return film.locked(st, i)

    def film_period(self, st, i, f, days):
        film.shoot(st, i, f, days)

    def film_breach(self, st):
        film.breach_month(st, st.ym + 1)

    def period_start(self, st, i, entry):
        self.cur_period = i
        events.period_start(self, st, i, entry)

    def period_end(self, st, i, entry, out):
        events.period_end(self, st, i, entry, out)

    def day(self, st, day):
        events.day(self, st, day)

    def outing(self, st, place):
        events.outing(self, st, place)

    def vacation(self, st, table):
        events.vacation(self, st, table)

    def class_chain(self, st, chain, n):
        events.class_chain(self, st, chain, n)

    def book_done(self, st, bid):
        events.book_done(self, st, bid)

    def job_period(self, st, jid, good):
        events.job_period(self, st, jid, good)

    # ---------- 月末、月结 ----------
    def month_events(self, st):
        events.month_end(self, st)

    def release(self, st):
        film.release(st)

    def rival_growth(self, st):
        """有名对手按 rivals.json 的“自”日期换阶段，无名对手按半年数算，10 月不用另做。"""

    def annual(self, st):
        events.annual(self, st)

    def era(self, st, ids):
        events.era(self, st, ids)

    def ending(self, st):
        ending.judge(st)


def new_game(seed=1, origin=(0, 0, 0), agent=None, data=None):
    return Game(data or load(), seed=seed, origin=origin, hooks=Story(agent))


def fit_plan(g, plan):
    """把固定日程里本月不能排的项换成在家休息（生病不能逛街、书读完了、工还没解锁…）。"""
    st = g.st
    out = []
    for i, e in enumerate(plan):
        if g.hooks.locked(st, i) or schedule.validate(st, e) is None:
            out.append(e)
        else:
            out.append('rest_home')
    return out


def run(seed, origin, plan, agent=None, data=None):
    """固定日程跑一局（不能排的旬改在家休息）。返回 (每月对账行, Game)。"""
    g = new_game(seed, origin, agent, data)
    lines = []
    while not g.st.finished:
        date = g.st.date
        g.start_month()
        p = plan(g) if callable(plan) else plan
        g.run_month(fit_plan(g, p))
        lines.append(trace_line(g.st, date))
    return lines, g


def main():
    ap = argparse.ArgumentParser(description='固定日程、SimpleAgent 跑完一局，每月一行状态，最后输出结局')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--origin', default='0,0,0', help='开局三问的选项序号，从 0 数')
    ap.add_argument('--plan', default='class_acting,job_dock,rest_home', help='每月三旬的日程')
    a = ap.parse_args()
    origin = tuple(int(x) for x in a.origin.split(','))
    lines, g = run(a.seed, origin, a.plan.split(','))
    for line in lines:
        print(line)
    st = g.st
    fs = film.films(st)
    print(f"片约 {len(fs)}：" + ' '.join(f"{f['档次']}{'配' if f['配角'] else ''}{f['状态']}" for f in fs))
    print(f"结局 {st.story['结局']}")


if __name__ == '__main__':
    main()
