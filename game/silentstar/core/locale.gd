extends RefCounted
## Runtime translations: reads data/locale/text.csv (key,zh_CN,en) and registers one Translation per locale column with the
## TranslationServer. Reads the file directly, so it does not depend on the editor's CSV import. Empty cells are not registered:
## a missing translation shows the key itself (tools/check.py lists how many lines still lack English).
##
##   Locale.load_csv()                      # at start-up
##   TranslationServer.set_locale("en")
##   tr("item.gold_watch.name")             # or TranslationServer.translate(key)

const Rules = preload("res://core/rules.gd")


static func default_path() -> String:
	return ProjectSettings.globalize_path("res://").path_join("../../data/locale/text.csv").simplify_path()


## Returns the number of keys registered, or -1 when the file cannot be read.
static func load_csv(path := "") -> int:
	if path == "":
		path = default_path()
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("cannot open %s (%d)" % [path, FileAccess.get_open_error()])
		return -1
	var head := f.get_csv_line()
	if head.size() < 2 or head[0] != "key":
		push_error("%s: the first column must be key" % path)
		return -1
	var tr_by_col := []
	for i in range(1, head.size()):
		var t := Translation.new()
		t.locale = head[i]
		tr_by_col.append(t)
	var n := 0
	while not f.eof_reached():
		var row := f.get_csv_line()
		if row.size() < 2 or row[0] == "":
			continue
		n += 1
		for i in range(1, mini(row.size(), head.size())):
			if row[i] != "":
				tr_by_col[i - 1].add_message(row[0], row[i])
	for t in tr_by_col:
		TranslationServer.add_translation(t)
	return n


## Display name of an ending. An ending with dynamic_name has a placeholder {<variable>} in its name
## (for example "{top_job}"), replaced by the display name of the job the variable holds.
static func ending_name(st, ending: Dictionary) -> String:
	var name := TranslationServer.translate("ending.%s.name" % ending["id"])
	var dyn = ending.get("dynamic_name")
	if dyn != null:
		name = name.replace("{%s}" % dyn, TranslationServer.translate("job.%s.name" % Rules.get_var(st, dyn)))
	return name
