"""Auditions (GDD 7, 9): deck building, effective points, play habits, rival decks, result tiers.

Colors are 0-3 in the order tough/lover/culture/savvy (habits.json audition.color_order).
A card is (color, points). Effective points are integers scaled by x100 (GDD 16).

Random-number order (Godot copies this):
- Unnamed rival: r(main_level random), then the habit with below(6).
- One match: draw the style with below(100) first; then each round the rival plays first (unless the habit is
  random: first roll 80% whether to follow the habit; if not following, or random, below(remaining cards)),
  then the player is asked.
- Botched: roll report_prob.
How the player builds a deck and plays is not decided here: a Player (UI or bot) is passed in.
"""
from . import rules

COLORS = 4


def cfg(d):
    return d.t['habits']['audition']


def color_names(d):
    return cfg(d)['color_order']


def beats(d):
    """Counter ring: beats[a] = the color that a counters."""
    c = cfg(d)
    names = c['color_order']
    return [names.index(c['counters'][n]) for n in names]


# ---------- cards ----------
def build_deck(levels, colors):
    """The colors the player picks for the 5 cards; the k-th card of one color (k from 0) has points = max(0, road level - k) (7.2)."""
    seen = [0] * COLORS
    out = []
    for c in colors:
        out.append((c, max(0, levels[c] - seen[c])))
        seen[c] += 1
    return out


def deck_of(levels, main, k, sub, n=5):
    """k cards of the main color plus 5-k of the second color."""
    return build_deck(levels, [main] * k + [sub] * (n - k))


def effective(d, a, b, field):
    """Effective points (va, vb) of the two cards in one round, x100 integers (7.3)."""
    c = cfg(d)
    bt = beats(d)
    (ca, pa), (cb, pb) = a, b
    va, vb = pa * 100, pb * 100
    if ca == field:
        va = va * c['style_pct'] // 100
    if cb == field:
        vb = vb * c['style_pct'] // 100
    if bt[ca] == cb and cb != field:
        va = va * c['counter_pct'] // 100
        vb = vb * c['countered_pct'] // 100
    elif bt[cb] == ca and ca != field:
        vb = vb * c['counter_pct'] // 100
        va = va * c['countered_pct'] // 100
    return va, vb


def round_winner(d, mine, theirs, field, fame_me, fame_them):
    """True when the player wins this round. Ties go to fame, and on equal fame the rival wins (7.3)."""
    va, vb = effective(d, mine, theirs, field)
    if va != vb:
        return va > vb
    return fame_me > fame_them


def solo_value(d, card, field):
    """Used to rank "big/small": counts the style only, no counters (7.6)."""
    v = card[1] * 100
    if card[0] == field:
        v = v * cfg(d)['style_pct'] // 100
    return v


# ---------- rivals ----------
def guard_color(d, main):
    """Counter of counter: whoever counters the color that counters main (lover -> savvy, tough -> culture)."""
    bt = beats(d)
    beater = bt.index(main)
    return bt.index(beater)


def opponent_colors(d, levels, probs):
    """The rival's (main color, second color) (7.5): the main color maximizes level x (1 + 0.3 x style probability), ties go to the earlier color;
        the second color is the counter of counter, to avoid being countered."""
    co = cfg(d)['rival_deck']['style_factor_pct']
    key = [levels[c] * (10000 + co * probs[c]) for c in range(COLORS)]
    main = min(range(COLORS), key=lambda c: (-key[c], c))
    return main, guard_color(d, main)


def opponent_deck(d, rival, probs):
    main, sub = opponent_colors(d, rival['levels'], probs)
    return deck_of(rival['levels'], main, rival['k'], sub)


def half_years(st):
    return st.ym // 6


def unnamed_rival(st, tier, main_level=None, probs=None):
    """Unnamed rival (9.2). Main color = the color with the highest style probability, second color = counter of counter (level main-2), the other two colors level 1."""
    d = st.d
    g = st.rng.logic
    r = d.t['rivals']['unnamed']
    t = next(x for x in r['tier'] if x['size'] == tier)
    h = half_years(st)
    if main_level is None:
        L = t['main_level']['base'] + sum(1 for m in t['main_level']['level_up_months'] if st.date >= m) + g.r(*t['main_level']['random'])
    else:
        L = main_level
    L = max(1, L)
    probs = probs or [25, 25, 25, 25]
    main = min(range(COLORS), key=lambda c: (-probs[c], c))
    lv = [1] * COLORS
    lv[main] = L
    lv[guard_color(d, main)] = max(1, L - t['second_gap'])
    habits = d.t['habits']['habits']
    hb = habits[g.below(len(habits))]['id']
    return {'id': None, 'name': f'unnamed ({tier})', 'levels': lv,
            'fame': t['fame']['base'] + t['fame']['per_half_year'] * h, 'habit': hb, 'k': t['k']}


def named_rival(st, rid):
    """Named rival's data for the current month (9.1). From 1927-09 Valen is replaced by Nova or Jilbo (9.3); one is drawn."""
    d = st.d
    rv = d.t['rivals']
    date = st.date
    for x in rv['replace']:
        if x['old'] == rid and date >= x['from']:
            rid = x['new'][st.rng.logic.below(len(x['new']))]
    r = next(x for x in rv['named'] if x['id'] == rid)
    lv = fame = None
    for s in r['stages']:
        if date >= s['from']:
            lv = s['levels']
            fame = s.get('fame', fame)
    return {'id': rid, 'name': r['name'], 'levels': list(lv), 'fame': fame, 'habit': r['habit'], 'k': r['k']}


def rival_present(st, rid):
    r = next(x for x in st.d.t['rivals']['named'] if x['id'] == rid)
    return r['present'][0] <= st.date <= r['present'][1]


# ---------- play habits ----------
def opponent_pick(st, habit, hand, field, rnd, my_last, score):
    """Which card (index into hand) the rival plays this round. score = (player round wins, rival round wins)."""
    d = st.d
    g = st.rng.logic
    if habit != 'habit_random':
        follow = g.chance(d.t['habits']['follow_prob'], 100)
    else:
        follow = False
    if not follow:
        return g.below(len(hand))
    order = sorted(range(len(hand)), key=lambda i: (solo_value(d, hand[i], field), i))   # smallest to largest
    small, big = order[0], order[-1]
    if habit == 'habit_lead':
        return big
    if habit == 'habit_finish':
        return small
    if habit == 'habit_open':
        return big if rnd == 0 else small
    if habit == 'habit_follow':
        if rnd == 0:
            return order[len(order) // 2]
        for i in order:
            va, vb = effective(d, my_last, hand[i], field)
            if vb > va:
                return i
        return small
    if habit == 'habit_score':
        me, them = score
        return big if them <= me else small
    raise ValueError(habit)


# ---------- player ----------
class Player:
    """The UI or a bot implements these two methods."""

    def deck(self, st, ctx):
        """Returns 5 colors (0-3). ctx: role, round number, rival (only the intel the player can see), own levels."""
        raise NotImplementedError

    def play(self, st, ctx):
        """Returns the index of the card to play from own hand. ctx: hand, rival's remaining hand, style, round, score, history."""
        raise NotImplementedError


class FixedRandomPlayer(Player):
    """Fixed deck, random play (for tests and rough estimates). Playing uses the logic stream."""

    def __init__(self, colors):
        self.colors = colors

    def deck(self, st, ctx):
        return list(self.colors)

    def play(self, st, ctx):
        return st.rng.logic.below(len(ctx['hand']))


# ---------- one match ----------
def roll_field(st, probs):
    v = st.rng.logic.below(100)
    acc = 0
    for c in range(COLORS):
        acc += probs[c]
        if v < acc:
            return c
    return COLORS - 1


def match(st, my_deck, rival, probs, player, field=None):
    """Plays one match. Returns {'score_line': (me, rival), 'style', 'rounds': [(my card, rival card, I won)]}."""
    d = st.d
    need = cfg(d)['rounds_to_win']
    their_deck = opponent_deck(d, rival, probs)
    if field is None:
        field = roll_field(st, probs)
    mine, theirs = list(my_deck), list(their_deck)
    me = them = 0
    hist = []
    my_last = None
    fame_me = st.attr['fame']
    rnd = 0
    while me < need and them < need and mine:
        oi = opponent_pick(st, rival['habit'], theirs, field, rnd, my_last, (me, them))
        ctx = {'hand': list(mine), 'rival_hand': list(theirs), 'style': field, 'round': rnd,
               'score_line': (me, them), 'history': list(hist), 'opponents': rival}
        mi = player.play(st, ctx)
        a, b = mine.pop(mi), theirs.pop(oi)
        win = round_winner(d, a, b, field, fame_me, rival['fame'])
        me += win
        them += not win
        hist.append((a, b, win))
        my_last = a
        rnd += 1
    return {'score_line': (me, them), 'style': field, 'rounds': hist, 'rival_cards': their_deck, 'my_cards': list(my_deck)}


# ---------- results ----------
def player_levels(st):
    b = st.bonus()
    lv = []
    for r in st.d.roads:
        rep = st.rep(r, b)
        L = 0
        for i, g in enumerate(st.d.level_gate):
            if rep >= g:
                L = i
        lv.append(L)
    return lv


def player_main(st):
    """The player's main color: the road with the highest current reputation, ties go to the earlier one."""
    b = st.bonus()
    reps = [st.rep(r, b) for r in st.d.roads]
    return max(range(COLORS), key=lambda c: (reps[c], -c))


def remembered_probs(probs, main, pts):
    """Remembered by the director: the player's main color +pts percentage points, taken from the highest other color (7.4)."""
    p = list(probs)
    others = [c for c in range(COLORS) if c != main]
    top = max(others, key=lambda c: (p[c], -c))
    move = min(pts, p[top])
    p[main] += move
    p[top] -= move
    return p


def classify(d, score):
    me, them = score
    if me >= cfg(d)['rounds_to_win']:
        return 'remembered' if them == 0 else 'won'
    if (me, them) == tuple(cfg(d)['result']['narrow_loss']['score_line']):
        return 'narrow_loss'
    if me == 0:
        return 'botched'
    return 'lost'


def audition(st, role, player, rivals, probs=None):
    """One audition. rivals: the rival list (1 for small/medium films, 2 for big films; made by the board).
        probs: the style probabilities for this audition (default the role's; remembered, tutorial role etc. are computed by the caller first).
        Returns {'result': won/narrow_loss/lost/botched, 'remembered': bool, 'rounds': [match ...]} and settles 7.4 fame, report and duels."""
    d = st.d
    probs = probs or role['style_probs']
    res = cfg(d)['result']
    out = {'roles': role['id'], 'rounds': [], 'remembered': False}
    final = None
    for n, rv in enumerate(rivals):
        ctx = {'roles': role, 'rounds': n, 'opponents': rv, 'levels': player_levels(st)}
        colors = player.deck(st, ctx)
        if len(colors) != cfg(d)['cards'] or any(not 0 <= c < COLORS for c in colors):
            raise ValueError(f'bad deck: {colors}')
        m = match(st, build_deck(ctx['levels'], colors), rv, probs, player)
        out['rounds'].append(m)
        if rv['id']:
            st.inc('duels.' + rv['id'])
        kind = classify(d, m['score_line'])
        if n == 0:
            final = kind
            out['remembered'] = kind == 'remembered'
            if kind not in ('won', 'remembered'):
                break
        else:   # Second match of a big film: you only get the role by winning; a loss always counts as narrow_loss
            final = final if kind in ('won', 'remembered') else 'narrow_loss'
            out['remembered'] = out['remembered'] and kind in ('won', 'remembered')
    if final == 'remembered':
        final = 'won'
    if final == 'botched':
        x = res['botched']
        rules.apply_effect(st, x['effect'], source='schedule')
        rules.apply_effect(st, x['favor'], source='schedule')
        if st.rng.logic.chance(*x['report_prob']):
            st.exposed = 1
            rules.apply_effect(st, x['report_effect'], source='schedule')
            out['reported'] = True
    if out['remembered']:
        st.flags['remembered.' + role['id']] = 1
    out['result'] = final
    return out


# ---------- GDD 7.7 table ----------
# A realistic setup: one lover role (style 15/60/10/15), the rival builds its deck by the 9.2 unnamed rule
# (3 lover cards + 2 savvy cards, second color 2 levels lower); the style is drawn from the role's probabilities; both sides play at random.
# The player takes the best-winning deck among "mono / main color 4 or 3 cards + one second color". Colors: 0 tough, 1 lover, 2 culture, 3 savvy.
ROLE_77 = [15, 60, 10, 15]
OPP_77 = 6
CASES_77 = [
    ('same road, same level', [2, 6, 2, 2]),
    ('same road, 1 level lower', [2, 5, 2, 2]),
    ('same road, 1 level higher', [2, 7, 2, 2]),
    ('same road, 2 levels higher', [2, 8, 2, 2]),
    ('same road, same level, tough as second road at 4', [4, 6, 2, 2]),
    ('tough-road player (T 6, L 2)', [6, 2, 2, 2]),
    ('culture-road player (C 6, L 2)', [2, 2, 6, 2]),
    ('savvy-road player (S 6, L 2)', [2, 2, 2, 6]),
]


def opp_77(d, L=OPP_77, probs=ROLE_77):
    t = d.t['rivals']['unnamed']['tier'][1]
    main = min(range(COLORS), key=lambda c: (-probs[c], c))
    lv = [1] * COLORS
    lv[main] = L
    lv[guard_color(d, main)] = max(1, L - t['second_gap'])
    return {'id': None, 'name': 'unnamed', 'levels': lv, 'fame': 100, 'habit': 'habit_random', 'k': t['k']}


def exact_win(d, my_deck, their_deck, field, fame_me=0, fame_them=100):
    """Win rate when both sides play at random: enumerate the 120 orderings of the rival's plays (my own order does not matter)."""
    import itertools
    need = cfg(d)['rounds_to_win']
    win = total = 0
    for p in itertools.permutations(range(len(their_deck))):
        me = them = 0
        for i, j in enumerate(p):
            if me >= need or them >= need:
                break
            if round_winner(d, my_deck[i], their_deck[j], field, fame_me, fame_them):
                me += 1
            else:
                them += 1
        win += me >= need
        total += 1
    return win / total


def candidate_decks(levels):
    """Main color = the color with the highest level; mono, or main color 4/3 cards plus one second color. Returns {name: color list}."""
    names = ['T', 'L', 'C', 'S']
    main = max(range(COLORS), key=lambda c: (levels[c], -c))
    out = {'mono': [main] * 5}
    for k in (4, 3):
        for s in range(COLORS):
            if s != main:
                out[f'{k}+{5 - k}{names[s]}'] = [main] * k + [s] * (5 - k)
    return out


def table_77(d, fame_hi=False):
    """Each row: (case, best deck, win rate, when style = lover, when style = another color); win rates are 0-1."""
    fm, ft = (200, 100) if fame_hi else (0, 100)
    rv = opp_77(d)
    theirs = opponent_deck(d, rv, ROLE_77)
    out = []
    for name, lv in CASES_77:
        best = None
        for dn, cols in candidate_decks(lv).items():
            mine = build_deck(lv, cols)
            per = [exact_win(d, mine, theirs, f, fm, ft) for f in range(COLORS)]
            tot = sum(ROLE_77[f] * per[f] for f in range(COLORS)) / 100
            if best is None or tot > best[2]:
                main_f = max(range(COLORS), key=lambda c: (ROLE_77[c], -c))
                rest = sum(ROLE_77[f] * per[f] for f in range(COLORS) if f != main_f) / (100 - ROLE_77[main_f])
                best = (name, dn, tot, per[main_f], rest, cols)
        out.append(best)
    return out


if __name__ == '__main__':
    from .data import load
    d = load()
    rv = opp_77(d)
    names = ['T', 'L', 'C', 'S']
    print(f'GDD 7.7: lover role (style {ROLE_77}), rival cards '
          + ' '.join(f'{names[c]}{p}' for c, p in opponent_deck(d, rv, ROLE_77)) + '; both sides play at random')
    a, b = table_77(d), table_77(d, fame_hi=True)
    for x, y in zip(a, b):
        print(f'{x[0]:<16} {x[1]:<5} rival fame high {x[2]*100:3.0f}% (lover style {x[3]*100:3.0f}% / other {x[4]*100:3.0f}%)'
              f'  my fame high {y[2]*100:3.0f}%')
