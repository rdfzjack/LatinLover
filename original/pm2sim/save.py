"""Save file F1xx.GNX (6930 bytes), written by 0389:4426 and read by 0389:45CD.

header: "PM2/ver1.02\\0", u16 0x2C, first name[18], family name[18], year, month, weekday, day
then u16 nblocks(10) and for each block u16 nwords + words (block table ds:4194 / sizes ds:41A8),
4 name buffers (u16 len + bytes), ROOM_PIC, DRESS_NUM, the DRESS / EQUIP / ARMS slots,
ITEM_MAX, ITEM_DIM(50) and 50 item records, and the health-care string.
"""
import struct

MAGIC = b'PM2/ver1.02\0'
BLOCKS = [(0x41BC, 10), (0x41D0, 45), (0x422A, 2), (0x423A, 19), (0x42FC, 5), (0x4306, 22),
          (0x5A00, 161), (0x5B42, 7), (0x5B50, 147), (0x5C76, 14)]
L_NAME, L_FAM = 32, 32          # ds:422E, ds:4230
L_IN, L_IP, L_IH = 16, 64, 18   # ds:4332, ds:4334, ds:4336
FILE_SIZE = 0x1B58 - 70         # the game always writes 6930 bytes


def _layout(vm):
    """Yield ('w', addr) for words and ('s', ptr_addr, length) for string buffers, in file order."""
    for a, n in BLOCKS:
        yield ('c', n)
        for k in range(n): yield ('w', a + 2*k)
    for p, ln in ((0x4232, L_NAME), (0x4234, L_NAME), (0x4236, L_FAM), (0x4238, L_FAM)):
        yield ('s', p, ln)
    for a in (0x4338, 0x433A, 0x433C, 0x433E): yield ('w', a)
    for p, ln in ((0x4340, L_IN), (0x4342, L_IP), (0x4344, L_IH)): yield ('s', p, ln)
    for base in (0x4346, 0x4350):
        yield ('w', base); yield ('w', base + 2)
        for k, ln in enumerate((L_IN, L_IP, L_IH)): yield ('s', base + 4 + 2*k, ln)
    yield ('w', 0x435A); yield ('w', 0x435C)
    for i in range(50):
        for arr in (0x435E, 0x43C2, 0x4426): yield ('w', arr + 2*i)
        for arr, ln in ((0x448A, L_IN), (0x44EE, L_IP), (0x4552, L_IH)): yield ('s', arr + 2*i, ln)
    yield ('s', 0x5C94, 16)


def load(vm, data):
    if data[:11] != MAGIC[:11]: raise ValueError('not a PM2 save')
    p = 12 + 2 + struct.unpack_from('<H', data, 12)[0]
    nblocks = struct.unpack_from('<H', data, p)[0]; p += 2
    assert nblocks == len(BLOCKS)
    for item in _layout(vm):
        if item[0] == 'c': p += 2
        elif item[0] == 'w':
            vm.ww(item[1], struct.unpack_from('<H', data, p)[0]); p += 2
        else:
            ln = struct.unpack_from('<H', data, p)[0]; p += 2
            dst = vm.ruw(item[1]); vm.mem[dst:dst+ln] = data[p:p+ln]; p += ln
    return p


def dump(vm):
    out = bytearray(MAGIC) + struct.pack('<H', 0x2C)
    out += bytes(vm.mem[vm.ruw(0x4232):vm.ruw(0x4232)+18]) + bytes(vm.mem[vm.ruw(0x4236):vm.ruw(0x4236)+18])
    out += struct.pack('<4H', *(vm.ruw(a) for a in (0x5C76, 0x5C78, 0x5C7A, 0x5C7C)))
    out += struct.pack('<H', len(BLOCKS))
    for item in _layout(vm):
        if item[0] == 'c': out += struct.pack('<H', item[1])
        elif item[0] == 'w': out += struct.pack('<H', vm.ruw(item[1]))
        else:
            src = vm.ruw(item[1]); out += struct.pack('<H', item[2]) + bytes(vm.mem[src:src+item[2]])
    return bytes(out) + bytes(max(0, 6930 - len(out)))
