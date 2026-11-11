extends RefCounted
## JSON reading and writing; the output is byte-identical to Python's
## json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).
##
## Godot's built-in JSON reads every number as float, and its key order and escaping differ from Python's, so this is written by hand.
## The data tables and saves hold only integers (data/new/README.md); after reading, floats with integer values are converted back to int.


## Reads a JSON file, numbers converted to int. Returns null on error.
static func read_file(path: String):
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("cannot open %s (%d)" % [path, FileAccess.get_open_error()])
		return null
	return parse(f.get_as_text())


static func parse(text: String):
	var j := JSON.new()
	if j.parse(text) != OK:
		push_error("JSON line %d: %s" % [j.get_error_line(), j.get_error_message()])
		return null
	return intify(j.data)


## Recursively turns floats with integer values into ints.
static func intify(v):
	match typeof(v):
		TYPE_FLOAT:
			if v == floorf(v) and absf(v) < 9007199254740992.0:
				return int(v)
			push_error("fractional number in the data: %s" % v)
			return v
		TYPE_ARRAY:
			var out := []
			for x in v:
				out.append(intify(x))
			return out
		TYPE_DICTIONARY:
			var out := {}
			for k in v:
				out[k] = intify(v[k])
			return out
	return v


## Deep copy (used for saves; cuts references like a Python json round trip).
static func copy(v):
	match typeof(v):
		TYPE_ARRAY:
			var out := []
			for x in v:
				out.append(copy(x))
			return out
		TYPE_DICTIONARY:
			var out := {}
			for k in v:
				out[_key(k)] = copy(v[k])
			return out
	return v


static func dumps(v) -> String:
	var parts := PackedStringArray()
	_write(v, parts)
	return "".join(parts)


static func _key(k) -> String:
	match typeof(k):
		TYPE_STRING, TYPE_STRING_NAME:
			return String(k)
		TYPE_INT:
			return str(k)
		TYPE_BOOL:
			return "true" if k else "false"
		TYPE_NIL:
			return "null"
	push_error("unsupported key: %s" % [k])
	return str(k)


static func _write(v, parts: PackedStringArray) -> void:
	match typeof(v):
		TYPE_NIL:
			parts.append("null")
		TYPE_BOOL:
			parts.append("true" if v else "false")
		TYPE_INT:
			parts.append(str(v))
		TYPE_FLOAT:
			if v == floorf(v) and absf(v) < 9007199254740992.0:
				parts.append(str(int(v)))
			else:
				push_error("fractional number in a save: %s" % v)
				parts.append(str(v))
		TYPE_STRING, TYPE_STRING_NAME:
			parts.append(quote(String(v)))
		TYPE_DICTIONARY:
			var keys := []
			var by_key := {}
			for k in v:
				var s := _key(k)
				keys.append(s)
				by_key[s] = v[k]
			keys.sort()   # Godot compares strings by code point, like Python's sort_keys
			parts.append("{")
			var first := true
			for s in keys:
				if not first:
					parts.append(",")
				first = false
				parts.append(quote(s))
				parts.append(":")
				_write(by_key[s], parts)
			parts.append("}")
		_:
			if typeof(v) == TYPE_ARRAY or typeof(v) >= TYPE_PACKED_BYTE_ARRAY:
				parts.append("[")
				var first := true
				for x in v:
					if not first:
						parts.append(",")
					first = false
					_write(x, parts)
				parts.append("]")
			else:
				push_error("unsupported type: %s" % [v])
				parts.append("null")


## String escaping, like Python ensure_ascii=False: only quotes, backslashes and 0x00-0x1f are escaped.
static func quote(s: String) -> String:
	var out := PackedStringArray()
	out.append("\"")
	for i in s.length():
		var c := s.unicode_at(i)
		if c == 0x22:
			out.append("\\\"")
		elif c == 0x5C:
			out.append("\\\\")
		elif c == 0x0A:
			out.append("\\n")
		elif c == 0x0D:
			out.append("\\r")
		elif c == 0x09:
			out.append("\\t")
		elif c == 0x08:
			out.append("\\b")
		elif c == 0x0C:
			out.append("\\f")
		elif c < 0x20:
			out.append("\\u%04x" % c)
		else:
			out.append(s[i])
	out.append("\"")
	return "".join(out)
