extends RefCounted
## Art lookup. The screens never load pictures by path: they ask for a kind and a list of keys (most specific first) and get the first
## file that exists, or null (then the screen draws its placeholder). To add art, drop a file in the folder, no code change:
##
##   res://assets/<kind>/<key>.png      (.webp, .jpg also work)
##
## Kinds and keys used by the screens:
##   cg        entry/<schedule entry>     "entry/class_boxing", "entry/rest_outing_place_dock" ("@" becomes "_")
##             entry_kind/<kind>          "entry_kind/class", "entry_kind/job", "entry_kind/book", "entry_kind/rest"
##             shoot/<film size>          "shoot/small", "shoot/medium", "shoot/big"
##             event/<event id>           "event/evt_arrest"
##             event_class/<class>        "event_class/month_end"
##             ending/<ending id>         "ending/act_legend"
##             ending_category/<category>
##   map       <location id>              the ids of data/new/map.json, e.g. "loc_home" (button picture), "background" (the map)
##   portrait  <npc id>                   "duv"
##   card      <colour id>                "tough", "lover", "culture", "savvy" (card back / face)
## Audio is looked up by the effects node (fx.gd), not here.

const ROOT := "res://assets/"
const EXTENSIONS := ["png", "webp", "jpg"]

static var _cache := {}


## The first existing picture of this kind for these keys, or null.
static func find(kind: String, keys: Array) -> Texture2D:
	for k in keys:
		var t := _load(kind, str(k))
		if t != null:
			return t
	return null


static func _load(kind: String, key: String) -> Texture2D:
	var id := kind + "/" + key
	if _cache.has(id):
		return _cache[id]
	var out: Texture2D = null
	for ext in EXTENSIONS:
		var path := "%s%s/%s.%s" % [ROOT, kind, key, ext]
		if ResourceLoader.exists(path):
			out = load(path)
			break
	_cache[id] = out
	return out


## Keys of the CG for a schedule entry ("class_boxing", "rest_outing@place_dock", "shooting"), most specific first.
static func entry_keys(entry: String, film_size := "") -> Array:
	if entry == "shooting":
		return ["shoot/" + film_size, "entry_kind/shoot"]
	var flat := entry.replace("@", "_")
	var kind := entry.get_slice("_", 0)
	return ["entry/" + flat, "entry/" + entry.get_slice("@", 0), "entry_kind/" + kind]
