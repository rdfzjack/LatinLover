# Implementation notes: structure, interfaces and details added in `sim/` and Godot

For whoever ports Godot (PLAN steps 9-12) or edits `sim/`. The rules are in `design/GDD.md`; this file records what the GDD does not say and what was filled in while writing the code. Godot must match `sim/` byte for byte, so copy these details exactly. Chinese names used in the design documents are looked up in `design/GLOSSARY.md`.

## Identifiers and ordering (step 9c-1)

- Everything technical is English: JSON field names, ids, enum values, names in effects and conditions, keys of the save, identifiers and strings in code, comments, check output. Chinese lives only in the display fields of the data tables (`name`, `text`, `body`, `question`, `film_title`, `content`, `identity`). `tools/migrate_ids.py` and `tools/i18n_map.json` record the rename; there are no aliases for the old Chinese ids.
- **Save format version 2** (`"version": 2`). `State.from_dict` refuses other versions. Count keys keep their prefixes: `class_periods.<class>`, `job_periods.<job>`, `road_periods.<road>`, `count.<name>`, `duels.<rival>`. Effect / condition names are split at the first `.` (`rules.split_name`), never sliced by length.
- **No behaviour may depend on the alphabetical order of a name.** Where an order matters it is the order of the data table: `Data.item_order` (items.json rows) for held items and gear, `Data.npc_order` for the `known` list, `Data.roads` / `Data.skills` for ties between roads and skills, explicit `order` fields for endings and month-end events. The rows of `items.json` are in the order the code used to sort the old Chinese ids, which keeps every number of `python3 -m sim.report` identical to the numbers before step 9c. A new item is appended at the end; a tie then goes to the older row.
- `sil_hint` breaks favor ties by the order of the romance lines (before: by the Chinese name, UI only).
- Rival `easter_egg: true` (before: the note started with a certain word).

## Structure of `sim/`

| File | Content | GDD |
|---|---|---|
| `rng.py` | PCG32, logic stream and show stream | 16 |
| `data.py` | loads the tables and builds the indexes | 16 |
| `state.py` | state, displayed values, reputation, indices, save / load | 2, 10, 14.1 |
| `rules.py` | conditions, effects, event checks, probabilities | 11.0, 16 |
| `schedule.py` | classes, books, jobs, rest | 5.1-5.5 |
| `street.py` | street, items and gear, Sil | 5.8, 14 |
| `month.py` | month flow, month settlement, reconciliation output | 4, 10 |
| `audition.py` | decks, effective points, play habits, rivals, result tiers | 7, 9 |
| `board.py` | casting board: building the board, placeholder roles, rivals, talkies, house roles, intel, sign-up and auditions; swap role and steal role; scripts | 3.3, 6, 11.1 |
| `film.py` | film contracts, shooting, fees, breaches, releases, tags and typing | 5.6, 8, 10 |
| `events.py` | event executor; month-end events and opportunities, period start, outings and NPC schedule, Duv, job hooks, eras, annual events | 5.4, 5.5, 11, 12 |
| `ending.py` | endings, character, destiny, total score; registers the derived variables of the endings | 15 |
| `bots.py` | 8 strategy bots (`only_tough` `only_lover` `only_culture` `only_savvy` `two_roads` `crime_line` `books_culture` `random_pick`) and `play(bot, seed)` | - |
| `report.py` | runs the bots in bulk and prints a report (<=60 lines); `--n` `--bots` `--random-play` `--no-buy` | PLAN 7 |
| `story.py` | `Story` (the implementation of `Hooks`), `Agent` (the questions the player answers), `SimpleAgent`, whole-game command line | 4 |

**Agent interface.** The UI and the bots inherit `story.Agent` (or `SimpleAgent` and override a few methods): `deck` and `play` (auditions), `pick_role` (which role to sign up for), `accept_support` (take a supporting part or not), `go_personally` (do the stunt yourself), `option` (event option), `annual` (annual event), `family` (the tag family for the transition), `suppress` (suppress a scandal), `month_start` (script writing, detox, news leaks and the street at month start). The caller supplies the schedule each month: `g = story.new_game(seed, origin, agent)`, then every month `g.start_month()`, `g.run_month(three periods)`; `story.fit_plan` replaces entries that cannot be scheduled with resting at home. The report takes its numbers from here: `st.story['films']` (size, support, performance, fee and release result per film: S / hit / flop / accent), `st.story['ending']`, the `count.*` entries of `st.count` (auditions, auditions won, releases, hits, flops, supports, breaches, arrests, scandals, opportunities, annual ranks ...), `g.hooks.boards` (audition results of each board), `g.hooks.log` (events that fired). One game takes about 0.02 s.

**State.** The state of step 6 is in `st.story` (part of the save; fields in `state.new_story`). `month.py` adds two hooks for it: `month_start` (after the board is built) and `period_end` (after every period); a collapse now calls the ending hook on the spot and ends the month settlement.

**Random-number conventions** (Godot copies them; details at the top of `rng.py`, `schedule.py`, `audition.py`, `board.py`, `film.py`, `events.py`): `r(a, a)` consumes no random number; classes and books roll `r0(fatigue)` then `r0(stamina/2)` every day; jobs roll the daily effects first, then the success lines; auditions draw the style first, and in every round the rival plays before the player is asked. The 64-bit states in a save are hex strings so that Godot's JSON reader does not lose precision.

## Rule details filled in while implementing (the user has not reviewed them one by one)

Whoever takes over: do not treat these as user decisions.

**Data tables (steps 2, 3)**
- Condition format: outer OR, inner AND, with the `in` comparator and `"@variable"` references.
- Advanced and monograph speech books are on the shelf from 1926-08. "The place Valen leaves" is `>= 1927-09`.
- Senior approval: tier 100 gives +5 to one skill of the road (pick one of three); tier 200 gives "the senior's gear (road)" (class and skill are placeholders); tier 300 sets a flag that an opportunity reads; tier 400 "the best gear" is not defined in the GDD, so for now it only sets a flag and the model defines a placeholder item in step 17.
- The resort has 3 empty placeholder events (`vac_1`-`vac_3` in `outing.json`); the skill of the "old book" is undecided and the item sits in `items.json`.
- Endings got fallbacks: actor "second line (rest)", lover category A with looks <500 merges into "salon owner / widow's companion", culture category S/A with discipline <50 merges into "screenwriter / tabloid writer", and the all-round category falls back to "back to Naples".
- The action-film director is resident in the studio area in `places.json`, but the GDD 5.5.2 gives him no schedule, so `npc_schedule.json` has no row for him (the check warns).
- Event id prefixes: `evt_` system, `era_` era, `job_<job>_r<n>` / `_m<n>` random and milestone events of jobs, `opp_` opportunities, `outing_` outings, `vac_` resort. Events with complex logic carry `code: true` and are implemented in step 6 following their `note`.
- All `body` fields are `null` until steps 16-18.

**Schedule and month settlement (step 4)**
- Class level counts the periods including the current one: periods 1-3 level 1, from period 4 level 2 (consistent with Duv's story at periods 4, 7, 10).
- A class day without enough money is skipped: no fee, no fatigue; a period in which no day was attended does not count.
- The two indices are computed at month settlement and kept for the whole month (as in the original); skipping work, employer refusal and hospital fees read this value.
- Gear bonuses apply to attributes too; conditions, success lines and checks use displayed values. The grooming coefficient of outfits uses the training value plus the non-outfit bonus.
- `road_periods.<road>`: a class counts for the road of the first skill of its gain (tutoring counts for culture), a book for the road of its skill, a job for the roads of the skills in its daily effect, only for successful periods (bootlegging counts for tough and savvy both).
- The +1 favor at loyalty >= 200 applies only to events and items; fixed favor in schedules and persuasion by Sil do not get it.
- The month after very sick: the period decides by itself whether the sanatorium can be paid (8 x days); if not it becomes resting at home.
- The accent bonus counts down by one after the three periods of every month and covers the next 4 months.
- Outing events fire in the middle of the period; per-day events such as birthdays are checked after that period is settled.
- When sick, the restaurant takes the money and has no effect. The hints of Sil's status use favor >= 60 on a romance line and fatigue >= 50 for now.

**Auditions (step 5)**
- Unnamed rivals: main color is the color with the highest style probability, second color the second highest (main - 2), the other two colors level 1; the minimum level is 1.
- When Valen is replaced, one of Nova and Jilbo is drawn at random.
- Habit ties on "big/small" go by hand order; "random" does not roll the 80%; "follow" uses the full comparison (counters included) for "can beat", equal points do not count as a win.
- Big films: only winning the first match 3:0 and also the second counts as "remembered".
- GDD 7.7's setup (role style, rival deck, player decks) follows the idea that "the rival fits the role", see `audition.CASES_77`.
- The counter multipliers 1.3/0.8 and k=3 for unnamed rivals are my choice from the trial calculations of 7.7 (the user agreed that the multipliers may drop and that the rival's deck must avoid counters).
- A botched audition gives Sil favor +2 (written in `favor_sources` of `romance.json`).
- The player's main color = the road with the highest current reputation, used for the style adjustment of "remembered".

**Rest (step 8b, rule changed by the user)**
- The `period_effect` of resting at home (Sil favor +2) is added after all days of the period, counted as a schedule source (loyalty >= 200 does not add more).
- Every outing goes through `rest_outing@<place>`: the money per day is the place's `cost` or `cost_by_fame_tier[fame tier]`, fatigue is the place's `fatigue_per_day`; on a day without enough money it counts as resting at home (-5, no Sil favor).
- The resort has no resident, so every time one event is drawn from its random table by weight (before: uniform `below(count)`; now like the other places).
- The sanatorium has `player_choice: false`: `schedule.validate` refuses it, only the month flow forces it after very sick.

**Table editing (step 9b)**
- The effects of an opportunity are written only in `opportunities.json`; the story event with the same id in `events.json` has an empty `effect`; when an opportunity fires at month end the story event goes first and then the opportunity's effect is added (before only the story event's effect applied, so the two places gave different numbers).
- Outing-related names are unified: the `trigger` of a chain is `"outing"`, the counter is `count.outing.<place>`.
- `check_data.py` dropped the hard-coded count checks (15 books, 15 jobs, 9 rivals, >=36 endings, 5/4/6 opening options, 4 lifestyles) and now only needs at least one, with unique ids; the rule tables (attributes, skills, calendar, habits, annual events) are still counted.

**Board, shooting, release (step 6)**
- When the role pool runs out, **placeholder roles** are generated (`roles.json` `defaults.placeholder_gen`): main color style 55, others 15; wants = one random skill of the main color's road (small 40, medium 60, big 80); the tag is one random tag of the set of the main color; the named rival of the second match of a big film is drawn 5:3:2 from the 3 present rivals with the highest main-color level (as in the rough-calculation script).
- The tutorial role of 1926-01 takes the second small slot; when "the other three colors share equally" does not divide evenly, the leftover 1 point goes to the earlier color (like 14/60/13/13).
- `talkie` of a role has three values: true always, false never, null by the GDD 6.4 ratio when the board is built (all 9 current roles are null). The 1927-10 board draws 1 among the null roles.
- Getting a supporting part also counts as "got a role on this board", no second try.
- The 3 house roles of a long contract are drawn from the roles the fame reaches.
- The extra small role after Valen's death ("exotic_lover" or "romance" tag): every board gets one more small role with one of the two tags until 1928-12.
- Widow investment, transition and script roles are added after the board's base roles. The transition's medium film is drawn from the tags of the family the player picked.
- Duv's tip-off: the GDD says "current or next board". The auditions are all done in the month-start board build, so a tip-off can only come later and always goes to the next board (reveals the style and tags of one medium or big role).
- A shooting day adds fatigue before the check; in_love 20% and reckless slacking apply to shooting as well (GDD 5.1); the injury of stunt_self is rolled after the check. Performance, fit, tag familiarity and box score are integers scaled x1000.
- Fee order: base -> stunt_self x130% -> support x40% -> x(400+negotiation)/400 -> contract x85%, rounded down at each step.
- A supporting part also multiplies fame, rep_bonus and **dividend** by 0.3 on release (the GDD only says fame and rep_bonus; the rough script multiplies the dividend too).
- The road that gets the rep_bonus on release = the road of the highest **base** style of the role (the remembered and house bonuses do not count).
- Low-budget typed = `lowbudget` count >= 4; "released when it drops below 3" is read as <= 3, so no extra state is kept.
- Breaches (very sick, missing, withdrawal, a month-taking opportunity) do not release and cost fame -10%. A shoot locked into a month that is voided later always counts as a breach.
- A swap role is a medium film (fee 800, B=100) shot for 1 period; if the next period is already taken by another film it does not fire. A lost steal role voids the contract and fame stays.
- The October "rival growth" is not a separate step: named rivals change stage at their `from` date in `rivals.json`, unnamed rivals by the half-year count.

**Events (step 6)**
- At most 2 month-end events per month, opportunities included (after senior approval). Events squeezed out are judged again next month; if the cond has passed they are gone (e.g. New Year only in January).
- A job's `period_random` rolls every period whether the period succeeded or not; each milestone fires once. Successful periods meet the function NPC of the job.
- Arrest: the loyalty bail and the bar owner milestone's "fine halved" do not stack. Bar bouncer and bootlegging arrest on the spot when the check fails; a sick player is not arrested.
- Scandal: the newspaper line suppresses for free once a year, 200 suppresses without limit, both decided by the player (`Agent.suppress`); "know a month early" is simplified to "may pay 200 when the scandal happens". An official warning doubles the fame loss of the next scandal and is used up.
- Creditor: the dock countryman blocks once (the flag records it as used) -> loyalty >= 150 a friend covers it -> fight >= 50 drives him off (crime +10, debt months reset) -> the item with the highest price (price > 0) is taken (its value pays the debt, down to 0) -> fame -10% and exposure.
- After a refused long contract nothing is offered for 3 months. The long contract's monthly pay comes before the month-end events.
- Outings: everyone present counts as "met"; when the people present have no chain or resident event to fire, the place's random table is used. The smuggling events mentioned in the dock milestone have no content yet and were not added.
- Tutoring period (at least one day attended): first "Duv starts writing the script", then the 1/10 tip-off. Duv's "education passed 100/200/300 +5 each" is checked every period after he is known (`education_milestones` of Duv in `romance.json`).
- Annual events: a rival score >= mine ranks ahead of me. The rivals do not include the easter-egg rival.
- The birthday date `events.json` evt_birthday.date is null (waiting for the user); null never fires; when it fires Sil and the actress get +3.
- Detox, leaking news and writing a script are month-start actions (`Story.send_detox` / `leak_news` / `write_script`).

**Endings (step 6)**
- Character score: of the 74 endings of the original only 4 are graded pine/bamboo/plum, the others are plum (-10). The new endings do not say which are graded yet, so all use plum; an ending may add `character: [{cond, tier}]` to override (`scoring.character_tiers` of `endings.json`). In step 18, when writing the ending texts, the model picks a few endings to grade, following the original ratio, without asking the user.
- The comment only gives the id of the class taken most (reading counts as one class `book`) and of the job done most; the text comes in step 18.
- Collapse mid-game: the ending is resolved on the spot, only the ending id and grade are recorded, no total score.

**Tables changed for code** (all just GDD rules written as data)
- `jobs.json`: bootlegging prerequisite gets "or flag.smuggling"; the newspaper helper and the studio office get `success_line_mods` (flag diploma education line -20).
- `stats.json`: fame decay written as `monthly_decay_pct` 2 and `monthly_decay_min` 1.
- `habits.json`: new `audition` block with the numbers of GDD section 7 (cards, rounds to win, counter ring, style 130, counter 150/70, rival deck coefficient 30, result tiers).
- `tools/check_data.py` checks them accordingly.
- Step 6: `roles.json` `defaults` got the blocks board, talkie, shoot, release, placeholder_gen, script; `stats.json` contract.long_contract (monthly pay 150, 3 house roles, style +10, refusal 3 months); `events.json` month_end_cap 2 and the `date` field of the birthday; `romance.json` Duv's education milestones; `endings.json` scoring.character_tiers. All are numbers already in the GDD.

When the GDD and the JSON disagree, ask the user first.

**Balance round (step 8): code and table changes made for the numbers**
- Growth of unnamed rivals: every tier of `rivals.json` has a `main_level.level_up_months` list, level = base + number of passed level-up months + random (before: a global "one level per three half-years").
- `items.json` gained dance shoes (clothing store) and a makeup case (general store), so lover-road gear can be bought.
- The S line of the endings is in `stats.json` `rep_rules.ending_grade_lines` and `endings.json` `grade_lines`; change both together.

## Godot (game/silentstar/, from step 9)

Godot 4.3, GDScript. The project is in `game/silentstar/`; the logic is in `core/` (independent of any node); the reconciliation script is in `tools/`. `.godot/` is the editor cache and not in git. Since step 9c-2 the Godot code uses the same English ids and the same data structure as `sim/`.

| File | Python counterpart | Content |
|---|---|---|
| `core/rng.gd` | `rng.py` | two PCG32 streams. The 64-bit state is split into a high and a low 32-bit number (GDScript ints are signed 64-bit and overflowing multiplication is unreliable); the split algorithm was checked against Python on 5000 numbers |
| `core/jsonx.gd` | - | JSON read / write. Read: float values that are integers are converted back to int (Godot reads every number as float). Write: byte-identical to Python `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',',':'))` |
| `core/data.gd` | `data.py` | loads the tables and builds indexes. Reads `data/new/` at the repository root by default (two levels above the project folder), shared with Python |
| `core/rules.gd` | `rules.py` | conditions, effects, checks, probabilities. All static functions; `extra_vars` is kept for the derived values of step 12. `split_name` splits at the first `.` |
| `core/state.gd` | `state.py` | state, displayed values, reputation, indices, save / load |
| `core/locale.gd` | - | reads `data/locale/text.csv` at run time and registers one `Translation` per locale column with the `TranslationServer` (no editor import needed); empty cells are not registered, so a missing translation shows the key. `ending_name` fills the `{top_job}` placeholder |
| `tools/trace.gd` | `tools/trace.py` | prints the reconciliation text for `tools/trace_cases.json` |

**Porting conventions**
- Scripts refer to each other with `preload("res://core/xxx.gd")`, not `class_name`: with `--script` in headless mode the global classes may not be registered yet.
- Python's `State.new(data, seed, origin)` is `State.new(data)` then `start(seed, origin)` in Godot; `State.loads` is `State.new(data)` then `loads(s)`. `st.month` and `st.date` are methods: `st.month()`, `st.date()`. `st.log` is renamed `debug_log` (`log` is a built-in function).
- Integers: `tdiv` truncates toward zero (GDScript `/` already does), `fdiv` is Python's `//`.
- Comparison: Python `==` between an int and a str gives False while GDScript raises an error, so `rules._cmp` compares the types first.
- Dictionary keys are strings; when writing a save the keys are sorted by code point, like Python. Renaming keys changed the order of `sort_keys` output; both sides sort by code point, so they still agree.
- `State.loads` / `from_dict` return false (and report an error) when the save version is not 2.
- Tie rules are the table orders of the section above: `_held` iterates `Data.item_order`, exclusive groups in order of first appearance.

**Reconciliation (completion standard of step 9)**, from the repository root:

```
godot --headless --path game/silentstar --script res://tools/trace.gd -- --out=work/trace_godot.txt
python3 tools/trace.py --out work/trace_py.txt
python3 tools/compare_trace.py work/trace_py.txt work/trace_godot.txt
```

`compare_trace.py` prints only the first differing line. The month-by-month reconciliation from step 10 on uses it too: add cases to `trace_cases.json` and one output section to each side's trace.

**When exporting**: the data tables live outside the project, so `data/new/` must be copied into the project before export (handled in step 13).

## Text and translations (step 9c-2)

- `tools/extract_text.py` holds the one list of display fields (`SPEC`) and writes `data/locale/text.csv` (`key,zh_CN,en`). Key: `<category>.<id>.<field>`; nested lists add `.option.<index>` (options have no id) or `.service.<id>`. `zh_CN` is regenerated on every run, `en` is kept. The Chinese an English line was written against is in `data/locale/en_basis.json`; if the Chinese differs the line is reported as a stale translation until `--ack`. `tools/check.py` runs the same code (step 4/5): missing Chinese, duplicate keys, keys without a record, stale English and Chinese outside the display fields are errors; lines without English are only counted.
- Decisions: tag families (`tag_families` in `endings.json`) have no display name; the family choice of the transition is shown through the member tags (`tag.<id>.name`). Add a name when a screen needs one. Endings with `dynamic_name: top_job` carry the placeholder `{top_job}` in their `name`; `locale.gd` `ending_name` replaces it by the translated name of the job held by that variable.
- `test_locale.py` covers the key format, stale / extra / duplicate keys and stray Chinese.
