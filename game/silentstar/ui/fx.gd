extends Node
## Effects and sound. The screens never play sounds or tweens by themselves: they announce what happened with cue(name, data) and
## this node decides what to do. To add an effect or a sound, nothing in the screens changes:
##
##   * drop a sound file res://assets/sfx/<cue name>.ogg (or .wav): it is played when the cue is announced;
##   * register a handler: fx.handlers["period_report"] = Callable(...) (called with the cue data, may use fx.host);
##   * or connect to the signal cue_played(name, data) from anywhere.
##
## Cues announced by the screens (see ui/README.md for the list with their data):
##   map_open, location_open, period_report, event_dialog, deck_open, round_open, card_play, reveal, round_win, round_lose,
##   audition_win, audition_lose, month_summary, annual_result, ending, save, load

signal cue_played(name: String, data: Dictionary)

const SFX_DIR := "res://assets/sfx/"

var host: Control                       # the node the default effects act on (set by the main screen)
var handlers := {}                      # cue name -> Callable(data: Dictionary)
var enabled := true
var _players := {}


func cue(cue_name: String, data := {}) -> void:
	if not enabled:
		return
	cue_played.emit(cue_name, data)
	_play_sound(cue_name)
	if handlers.has(cue_name):
		handlers[cue_name].call(data)


## Default effect for a freshly built screen: fade the content in.
func fade_in(node: CanvasItem, seconds := 0.2) -> void:
	if node == null or not enabled:
		return
	node.modulate.a = 0.0
	var tw := node.create_tween()
	tw.tween_property(node, "modulate:a", 1.0, seconds)


## Default effect for emphasis: a short colour pulse on a node.
func pulse(node: CanvasItem, color := Color(1, 1, 1), seconds := 0.25) -> void:
	if node == null or not enabled:
		return
	var tw := node.create_tween()
	tw.tween_property(node, "modulate", color, seconds * 0.5)
	tw.tween_property(node, "modulate", Color(1, 1, 1), seconds * 0.5)


func _play_sound(cue_name: String) -> void:
	for ext in ["ogg", "wav"]:
		var path := "%s%s.%s" % [SFX_DIR, cue_name, ext]
		if ResourceLoader.exists(path):
			var p: AudioStreamPlayer = _players.get(cue_name)
			if p == null:
				p = AudioStreamPlayer.new()
				p.stream = load(path)
				add_child(p)
				_players[cue_name] = p
			p.play()
			return
