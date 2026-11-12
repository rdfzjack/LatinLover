# Screens (`game/silentstar/ui/`)

How the screens are organised and where to plug in art, sound and effects. Nothing here needs a change in `core/`.

## Files

| File | Job |
|---|---|
| `main.gd` / `main.tscn` | the frame (status bar, body, log) and every question the game asks. The game runs on a worker thread; `ask(kind, payload)` puts a question on the screen and waits, `reply(value)` answers it |
| `ui_story.gd` | `Story` plus the calls to the screen (period report, event dialog, annual result, board results); `UiAgent` = the player's answers |
| `board_view.gd` `.tscn` | the casting board |
| `audition_view.gd` `.tscn` | deck pick, round, reveal |
| `cg_view.gd` `.tscn` | a picture slot (placeholder until a picture exists) |
| `ending_view.gd` `.tscn` | the ending page |
| `inventory_view.gd`, `journal_view.gd` | items and gear; the diary (schedule book of the people met, events so far) |
| `assets.gd` | finds pictures by kind and key |
| `fx.gd` | announces cues, plays sounds, default effects |
| `save_slots.gd` | save files |

## Text

No text in code. Every string a player can read is `tr("ui.<file>.<function>.<n>")` with its Chinese in `data/locale/ui.csv`
(`key,zh_CN,en`; an empty cell shows the key). Names of things (items, jobs, places ...) come from the `name` fields of the data tables.
`python3 tools/check_ui_text.py` (also step 5 of `tools/check.py`) fails when a string literal in `ui/*.gd` contains Chinese or a key is missing.
When you add text: write `tr("ui.main.my_function.1")` and add the row to `ui.csv`.

## Pictures

Put a file in `res://assets/<kind>/<key>.png` (`.webp`, `.jpg` also work). The screen shows it as soon as it exists. Keys, most specific first:

* `cg/entry/<entry>` (`entry/class_boxing`, `entry/rest_outing_place_dock`), `cg/entry_kind/<class|book|job|rest|shoot>`, `cg/shoot/<small|medium|big>`
* `cg/event/<event id>`, `cg/event_class/<class>`
* `cg/ending/<ending id>`, `cg/ending_category/<category>`
* `map/<location id>` and `map/background` (planned; the map still draws plain buttons), `portrait/<npc id>`, `card/<colour id>` (planned)

The keys are built in one place each (`Assets.entry_keys`, and the `show_cg` calls); to add a kind, add a lookup there.

## Effects and sound

The screens announce what happened with `fx.cue(name, data)`. `fx.gd` then (1) emits `cue_played(name, data)`, (2) plays `res://assets/sfx/<name>.ogg|wav` if it exists,
(3) calls `fx.handlers[name]` if one is registered. Cues: `map_open`, `location_open`, `month_start`, `period_report`, `event_dialog`,
`board_open`, `deck_open`, `round_open`, `card_play`, `reveal`, `round_win`, `round_lose`, `audition_win`, `audition_lose`, `month_summary`,
`annual_result`, `ending`, `save`, `load`. Each screen change also fades the body in (`fx.fade_in`); set `fx.enabled = false` to turn all of it off.

## Test modes

Arguments after `--`: `--auto` (plays itself, no screens), `--uitest` (builds and presses the screens), `--shot=file.png --shotkind=<question> [--shotloc=<place|reveal>]` (needs a display, see `design/IMPL_NOTES.md`), `--seed=N`, `--months=N`.
