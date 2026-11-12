extends RefCounted
## Save slots. A slot is a file user://save_<slot>.json = {"meta": {...}, "save": <the string of State.dumps()>}.
## Slot "auto" is written after every settled month; slots "1".."3" are written by the player between two months.

const SLOTS := ["auto", "1", "2", "3"]


static func path(slot: String) -> String:
	return "user://save_%s.json" % slot


static func exists(slot: String) -> bool:
	return FileAccess.file_exists(path(slot))


## meta: {date, money, fame_tier} for the list on the title screen.
static func write(slot: String, text: String, meta: Dictionary) -> bool:
	var f := FileAccess.open(path(slot), FileAccess.WRITE)
	if f == null:
		return false
	f.store_string(JSON.stringify({"meta": meta, "save": text}))
	return true


## {"meta": ..., "save": ...} or {} when the slot is empty or unreadable.
static func read(slot: String) -> Dictionary:
	if not exists(slot):
		return {}
	var j = JSON.parse_string(FileAccess.get_file_as_string(path(slot)))
	if j is Dictionary and j.has("save"):
		return j
	return {}
