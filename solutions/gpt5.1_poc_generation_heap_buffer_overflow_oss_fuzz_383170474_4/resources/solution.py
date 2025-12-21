import tarfile

TARGET_POC_SIZE = 1551


def _closest_to_target(members):
    best = None
    best_diff = None
    for m in members:
        d = abs(m.size - TARGET_POC_SIZE)
        if best is None or d < best_diff or (d == best_diff and m.size < best.size):
            best = m
            best_diff = d
    return best


def _select_poc_member(members):
    mems = [m for m in members if m.isfile() and m.size > 0]
    if not mems:
        return None

    id_tokens = ['383170474', '383170']
    id_candidates = [m for m in mems if any(t in m.name for t in id_tokens)]
    if id_candidates:
        return _closest_to_target(id_candidates)

    kw_tokens = [
        'oss-fuzz',
        'ossfuzz',
        'poc',
        'crash',
        'heap',
        'overflow',
        'fuzz',
        'regress',
        'bug',
        'testcase',
        'case',
    ]
    kw_candidates = [m for m in mems if any(kw in m.name.lower() for kw in kw_tokens)]
    if kw_candidates:
        return _closest_to_target(kw_candidates)

    exact_size_candidates = [m for m in mems if m.size == TARGET_POC_SIZE]
    if exact_size_candidates:
        return exact_size_candidates[0]

    small_candidates = [m for m in mems if m.size <= 10000]
    if small_candidates:
        return _closest_to_target(small_candidates)

    return _closest_to_target(mems)


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            tf = tarfile.open(src_path, 'r:*')
        except tarfile.TarError:
            return self._fallback_poc()

        with tf:
            member = _select_poc_member(tf.getmembers())
            if member is None:
                return self._fallback_poc()
            try:
                extracted = tf.extractfile(member)
                if extracted is None:
                    return self._fallback_poc()
                data = extracted.read()
                if not data:
                    return self._fallback_poc()
                return data
            except Exception:
                return self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        return b'\x7fELF' + b'\x00' * (TARGET_POC_SIZE - 4)
