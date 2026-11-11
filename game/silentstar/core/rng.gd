extends RefCounted
## Random numbers: PCG32 (XSH-RR, 64-bit state), two independent streams. Port of sim/rng.py.
##
## GDD 16: the logic stream is for rules, the show stream only for animation and text; they never affect each other.
## Conventions, the same as Python:
## - r(a, b) returns an integer in a..b (both ends included). When a == b it returns a without consuming a random number.
## - r0(n) = r(0, n); r1(n) = r(1, n).
## - below(n) returns 0..n-1, rejecting values below 2^32 mod n (unbiased).
## - chance(p, q) is below(q) < p; when p <= 0 or p >= q no random number is consumed.
##
## GDScript ints are signed 64-bit and overflowing multiplication is unreliable, so the 64-bit state is split into a high and a low 32-bit number.

class PCG32:
	extends RefCounted
	const M32 := 0xFFFFFFFF
	const MULT_HI := 0x5851F42D   # high 32 bits of 6364136223846793005
	const MULT_LO := 0x4C957F2D
	var hi := 0      # high 32 bits of the state
	var lo := 0      # low 32 bits of the state
	var inc_hi := 0
	var inc_lo := 0

	func _init(sd := 0, seq := 0, empty := false) -> void:
		if empty:
			return
		# inc = ((seq << 1) | 1) & MASK64
		inc_hi = (seq >> 31) & M32
		inc_lo = ((seq << 1) | 1) & M32
		hi = 0
		lo = 0
		next_u32()
		_add(sd)
		next_u32()

	## Multiplies two 32-bit numbers and returns [high 32 bits, low 32 bits]. Split into 16-bit halves; no intermediate value exceeds 2^34.
	static func _mul32(a: int, b: int) -> Array:
		var a0 := a & 0xFFFF
		var a1 := a >> 16
		var b0 := b & 0xFFFF
		var b1 := b >> 16
		var p00 := a0 * b0
		var p01 := a0 * b1
		var p10 := a1 * b0
		var p11 := a1 * b1
		var mid := (p00 >> 16) + (p01 & 0xFFFF) + (p10 & 0xFFFF)
		var l := ((mid & 0xFFFF) << 16) | (p00 & 0xFFFF)
		var h := p11 + (p01 >> 16) + (p10 >> 16) + (mid >> 16)
		return [h & M32, l & M32]

	## state += n (mod 2^64). n may be negative (two's complement), like Python's & MASK64.
	func _add(n: int) -> void:
		var n_hi := (n >> 32) & M32
		var n_lo := n & M32
		var s := lo + n_lo
		lo = s & M32
		hi = (hi + n_hi + (s >> 32)) & M32

	func next_u32() -> int:
		var old_hi := hi
		var old_lo := lo
		# state = old * MULT + inc
		var p := _mul32(old_lo, MULT_LO)
		var nh: int = p[0] + _mul32(old_lo, MULT_HI)[1] + _mul32(old_hi, MULT_LO)[1]
		var nl: int = p[1] + inc_lo
		lo = nl & M32
		hi = (nh + inc_hi + (nl >> 32)) & M32
		# output: x = low 32 bits of ((old >> 18) ^ old) >> 27; rot = old >> 59
		var sh_hi := old_hi >> 18
		var sh_lo := ((old_lo >> 18) | (old_hi << 14)) & M32
		var y_hi := sh_hi ^ old_hi
		var y_lo := sh_lo ^ old_lo
		var x := ((y_lo >> 27) | (y_hi << 5)) & M32
		var rot := old_hi >> 27
		return ((x >> rot) | (x << ((32 - rot) & 31))) & M32

	func below(n: int) -> int:
		if n <= 0:
			push_error("below(n) needs n >= 1")
			return 0
		var threshold := (0x100000000 - n) % n
		while true:
			var v := next_u32()
			if v >= threshold:
				return v % n
		return 0

	func r(a: int, b: int) -> int:
		if a == b:
			return a
		if b < a:
			push_error("r(%d,%d)" % [a, b])
			return a
		return a + below(b - a + 1)

	func r0(n: int) -> int:
		return r(0, n)

	func r1(n: int) -> int:
		return r(1, n)

	func chance(p: int, q: int) -> bool:
		if p <= 0:
			return false
		if p >= q:
			return true
		return below(q) < p

	## Save: 64-bit numbers are written as 16-digit hex strings
	func dump() -> Array:
		return [_hex8(hi) + _hex8(lo), _hex8(inc_hi) + _hex8(inc_lo)]

	static func load_from(d: Array) -> PCG32:
		var g := PCG32.new(0, 0, true)
		var s: String = d[0]
		var t: String = d[1]
		g.hi = s.substr(0, 8).hex_to_int()
		g.lo = s.substr(8, 8).hex_to_int()
		g.inc_hi = t.substr(0, 8).hex_to_int()
		g.inc_lo = t.substr(8, 8).hex_to_int()
		return g

	static func _hex8(v: int) -> String:
		const DIGITS := "0123456789abcdef"
		var s := ""
		for i in 8:
			s = DIGITS[v & 15] + s
			v >>= 4
		return s


## Two streams: logic (rules) and show (presentation). Derived from the same seed with different sequence numbers.
var logic: PCG32
var show: PCG32


func _init(sd := 0, empty := false) -> void:
	if empty:
		return
	logic = PCG32.new(sd, 1)
	show = PCG32.new(sd, 2)


func dump() -> Dictionary:
	return {"logic": logic.dump(), "show": show.dump()}


static func load_from(d: Dictionary):
	var g = load("res://core/rng.gd").new(0, true)
	g.logic = PCG32.load_from(d["logic"])
	g.show = PCG32.load_from(d["show"])
	return g
