# data/new: data tables of the new game

The rules and numbers live here; the game (Godot, `game/silentstar/core/`) reads them. The Python simulator `sim/` is frozen since step 12b and no longer follows them. To change a number, change only the JSON.
Validation: `python3 tools/check.py` (format, duplicates, content, event budget, and with Godot a bot playthrough with the balance guard; exit code 1 on errors). The step-by-step guide for editing tables is `data/USER_GUIDE.md`.

## Conventions

- **Ids, field names, enum values, names inside effects and conditions are English snake_case** (`stamina`, `job_bar`, `favor.sil`). The glossary Chinese | id | category is `design/GLOSSARY.md`.
- **Chinese appears only in display fields**, as the original text: `name` of every record, `text` of event / outing / opening options, `body` of events and endings, `question`, `film_title`, `content` of endings, `identity` of NPCs. Everything else (notes included) is English. There is no separate language file to edit when you add content: write the Chinese in the display field; `data/locale/text.csv` is generated from the tables by `tools/extract_text.py` (`tools/check.py` runs it); only its `en` column is edited by hand.
- Every record has an English `id`. A new record gets a new id and its Chinese `name`.
- Money and all numbers are integers; decimals are not allowed. Ratios are written as integer percentages (85 means x85/100) or `[numerator, denominator]`.
- A range `[a, b]` includes both ends; `add: [a, b]` means `r(a, b)`.
- All names are placeholders.
- The minus sign in effects and conditions is always ASCII `-`.
- **Row order is significant where ties are possible**: a tie between items goes to the earlier row of `items.json` (the rows are in the order the code used to sort the Chinese names, so the simulation results stayed identical); ties between roads, NPCs and skills go to the earlier row as well.

## Conditions

`[[ [variable, comparator, value], ... ], ... ]`: the outer list is OR, every inner list is AND. An empty list `[]` is always true.
Comparators: `>= <= > < == !=`, and `in`, whose value is a list, e.g. `["grade", "in", ["S", "A"]]`. A value written `"@variable"` compares with another variable, e.g. `["education", ">=", "@looks"]`.

Variables:

| Form | Meaning |
|---|---|
| `stamina` `education` ... `fame` `money` | base attributes |
| `fight` ... `insight` | skill displayed values |
| `sick_index` `reckless_index` | indices |
| `favor.sil` `favor.actress` | favor, −100 to 100 (NPC ids are in `romance.json`) |
| `favor_tier.<npc>` | favor tier: compare with `enemy` `at_odds` `known` `friendly` `close` `intimate` or 0-5 (`romance.json` rules.favor_tiers) |
| `job_periods.<job id>` | periods in which the job succeeded |
| `scale.<attr or skill>` | scale 0-100 (GDD 2.1.1): a base attribute is min(100, value x 10 / `stats.scale.div10`), a skill is its displayed value |
| `tier.<attr or skill>` | tier of the scale: compare with `low` `mid` `high` `very_high` or 0-3, e.g. `["tier.loyalty", ">=", "high"]` |
| `class_periods.<class id>` | periods spent in a class |
| `flag.<id>` | flag, value 1 or 0 |
| `date` | like `1927-04` |
| `tough` `lover` `culture` `savvy` | reputation of that road |
| `road_periods.<road>` | class + book + job periods of that road (used by senior approval) |
| `status.<id>` | boolean 1/0: `sick` `very_sick` `reckless` `in_love` `long_contract` `wrap_up` `shooting_period` `shoot_this_month` `has_pending_role` |
| `count.<id>` | free counters, e.g. `count.stunt_self`, `count.outing.place_dock` |
| `tag.<id>` | count of a film tag |
| `duels.<rival id>` | number of auditions against that rival |
| `max_rep` `month` `year` `drug_stage` `drug_points` `debt_months` | derived values |
| `grade` `top_tag_family` `undefined` `lowbudget_typed` `talkie_count` `top_base_attr` `top_savvy_skill` `max_job_periods` `rep_spread` `top_road` | derived values used by the endings |

## Effects

One line of text, terms separated by spaces, each term `name+n`, `name-n`, `name=n` (set to n) or `name+n%` (percentage of the current value), e.g. `stamina+20 discipline-15`. `trigger.<event id>` triggers another event next and has no number.
A name can be a base attribute, a skill, `money`, `drug_stage`, `drug_points`, `debt_months`, `favor.<npc>`, `rep_bonus.<road>` (reputation bonus), `weight.<tag>` (board weight +1), `item.<item id>` (=1 gains, =0 loses), `status.<id>`, `flag.<id>`.
`success_line_mods` of a job: `[{cond, stat, value}]`; when the cond holds, that stat's success line gets `value` added (e.g. flag `diploma` lowers the education line by 20).

Every event (`events.json`, `outing.json`) has a `tier`: `small`, `medium`, `large` or `bad`; each outcome must stay inside the tier's caps (`data/USER_GUIDE.md`, "Event budget"; checked by `tools/check_data.py`), unless the event has a `budget_note`.

Fields named `*_formula` hold a formula string interpreted by the code. `code: true` on an event means the logic is complex: the data only gives cond, prob and simple effects and the code implements the rest following the `note`.

## Checks

An event option's `check`: `null` always succeeds; a gate `[variable, comparator, value]`; or a d100 dice check `{"check": skill or base attribute, "diff": n}`: chance = scale − diff, clamped to `stats.json` check.min_pct..max_pct; `r1(100) <= chance` succeeds (`Rules.check_pct` gives the chance before the roll).

## Probability

`prob` of an event: `null` always; `[numerator, denominator]`; a tiered list `[{cond, value}]` takes the first whose cond holds (the last tier has an empty cond); `{numerator: variable, denominator: n, max: [p, q]}` (scandal exposure).

## Files

| File | Content | GDD |
|---|---|---|
| `stats.json` | attributes, money, roads, levels, fame tiers, indices, hidden values; `scale`; `check` (d100 dice limits); `drug` (boost action, drug stages) and `arrest` (fine, detention, `raid`: the month-end crime-job search) | 2, 5.8, 11.0, 11.2 |
| `skills.json` | the 12 skills | 2.2 |
| `classes.json` | the classes; `fatigue_per_day` per class; optional `success_stat` (the stat of the day roll instead of stamina) | 5.3.1 |
| `books.json` | book tiers and the book list; `fatigue_per_day` (a book matches its tier) | 5.3.2 |
| `jobs.json` | the 17 jobs, with unlocks, raises and hooks; `crime_job: true` marks a crime job (searched at month end); the old switched-off jobs carry `crime_tier` and `raid_*` | 5.4, 5.4.1 |
| `rest.json` | rests: at home (Sil keeps company), outing; the sanatorium is forced only when very sick (`player_choice: false`); `forced` has `discharge_effect` and `discharge_event` | 5.5 |
| `places.json` | outing places: cost (or by fame tier), fatigue change per day, residents, random table. One more row is one more place | 5.5.1 |
| `lifestyle.json` | lifestyles | 5.7 |
| `traits.json` | status traits shown on the status bar: `{id, name, body, cond, effects}`; a trait is on while its cond holds; `effects` only from `effects_allowed` (now `no_audition`) | 2.7 |
| `street.json` | street entries, shelves, services, discounts | 5.8 |
| `origins.json` | the three opening questions | 3.2 |
| `calendar.json` | days of the 48 months, Sundays, board, unlocks, era events | 1, 4 |
| `habits.json` | the 6 play habits and the intel rules; the `audition` block holds the numbers of section 7 (multipliers, counter ring, result tiers) | 7 |
| `rivals.json` | the 9 named rivals (stage by year), the unnamed rival formula, the replacement after Valen's death | 9 |
| `roles.json` | film tags (`tags`), roles (the 8 GDD examples plus 1 tutorial role; the other 51 come in PLAN steps 16, 17); `talkie` is true/false/null (null is decided by ratio when the board is built); `defaults` holds the rule blocks of step 6: board, talkie, shoot, release, placeholder generation, script | 6, 8 |
| `items.json` | items (row order matters, see Conventions) | 14 |
| `events.json` | period-start, month-end, era, job-hook and opportunity story events; `month_end_cap` is the most month-end events per month; the `date` ("MM-DD", null never fires) of the birthday | 8-12 |
| `outing.json` | random-table events of outings (resort included), NPC chains and resident events, tutoring chain events | 5.5, 11.4 |
| `romance.json` | the 4 romance lines and 8 function NPCs | 13 |
| `npc_schedule.json` | NPC schedule | 5.5.2 |
| `npc_chains.json` | order of chain and resident events | 5.5.2 |
| `annual.json` | annual events; `attend_effect` applies when attending | 12.1 |
| `opportunities.json` | opportunities | 12.2 |
| `endings.json` | forced, special, categories, endings, destiny, scoring (`character_tiers`: an ending may write `character: [{cond, tier}]`, otherwise the default tier is used) | 15 |

`body` (story text of events, ending text, magazine letters) is `null` everywhere; PLAN step 18 writes it.
The text inside events, film titles and the senior's gear skills are placeholders.
