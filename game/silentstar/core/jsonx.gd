extends RefCounted
## JSON 读写，输出和 Python 的
## json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')) 逐字节一致。
##
## Godot 自带的 JSON 把所有数字读成 float，键的排序和转义也和 Python 不完全一样，所以这里自己写。
## 数据表和存档里只有整数（data/new/README.md），读进来以后把整数值的 float 转回 int。


## 读一个 JSON 文件，数字转成 int。出错返回 null。
static func read_file(path: String):
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("打不开 %s（%d）" % [path, FileAccess.get_open_error()])
		return null
	return parse(f.get_as_text())


static func parse(text: String):
	var j := JSON.new()
	if j.parse(text) != OK:
		push_error("JSON 第 %d 行：%s" % [j.get_error_line(), j.get_error_message()])
		return null
	return intify(j.data)


## 递归把整数值的 float 变成 int。
static func intify(v):
	match typeof(v):
		TYPE_FLOAT:
			if v == floorf(v) and absf(v) < 9007199254740992.0:
				return int(v)
			push_error("数据里出现小数：%s" % v)
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


## 深拷贝（存档读写时用，和 Python 的 json 往返一样切断引用）。
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
	push_error("不支持的键：%s" % [k])
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
				push_error("存档里出现小数：%s" % v)
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
			keys.sort()   # Godot 的字符串比较按码位，和 Python 的 sort_keys 相同
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
				push_error("不支持的类型：%s" % [v])
				parts.append("null")


## 字符串转义，同 Python ensure_ascii=False：只转义引号、反斜杠和 0x00–0x1f。
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
