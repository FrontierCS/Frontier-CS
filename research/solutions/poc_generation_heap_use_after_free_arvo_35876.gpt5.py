import os
import re
from typing import List, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        project = self._detect_project(src_path)
        if project == "mruby":
            # Ruby-like script: allocate some heap, then trigger /= 0
            # Intentionally simple; many interpreters accept semicolons for multiple statements.
            return b's="X"*1048576;a=1;a/=0'
        if project == "berry":
            # Berry language is Python-like; try similar script.
            return b's="X"*1048576; a=1; a/=0'
        if project == "yasl":
            # YASL uses := for declaration.
            return b's := "X" * 1048576; a := 1; a /= 0;'
        if project == "kuroko":
            # Kuroko is Python-like.
            return b's="X"*1048576\na=1\na/=0\n'
        if project == "janet":
            # Janet Lisp-like; compound assignment might be (set x (/ x 0))
            return b'(def s (string/new 1048576)) (def a 1) (set a (/ a 0))'
        if project == "lua":
            # Lua doesn't have /=; simulate compound by reassigning.
            return b's=string.rep("X",1048576); a=1; a=a/0'
        if project == "wren":
            # Wren: var a = 1; a /= 0;
            return b'var s="X"*1048576; var a=1; a/=0;'
        if project == "python":
            return b's="X"*1048576\na=1\na/=0\n'
        if project == "php":
            # PHP: division by zero error on ints in newer versions.
            return b'<?php $s=str_repeat("X",1048576); $a=1; $a/=0;'
        if project == "quickjs" or project == "javascript" or project == "duktape" or project == "mujs":
            # JS: divide by zero is not error; try object to provoke error via valueOf throwing.
            # However stick to the described scenario; fallback to number division.
            return b'var s="X".repeat(1048576); var a=1; a/=0;'
        if project == "yara":
            # YARA lang doesn't support /=; fallback to expression.
            return b'/* Not applicable */'
        # Default fallback: Ruby-like script
        return b's="X"*1048576;a=1;a/=0'

    def _detect_project(self, src_path: str) -> str:
        # Heuristic project detection from source files
        indicators = self._scan_indicators(src_path)
        # mruby indicators
        if indicators.contains_any_name([
            "mruby.h", "mrbconf.h", "mruby", "include/mruby.h", "src/vm.c", "src/opcode.h", "mrb_"
        ]) or indicators.contains_any_content([
            r"\bmrb_", r"\bMRB_", r"ZeroDivisionError", r"MRB_TT_"
        ]):
            return "mruby"
        # Berry indicators
        if indicators.contains_any_name([
            "berry.h", "be_api.h", "be_vm.c", "be_exec.c", "berry"
        ]) or indicators.contains_any_content([
            r"\bbe_\w+", r"\bBE_", r"berry programming language"
        ]):
            return "berry"
        # YASL indicators
        if indicators.contains_any_name([
            "yasl.h", "YASL", "yasl-"
        ]) or indicators.contains_any_content([
            r"\bYASL\b", r"Yet Another Scripting Language"
        ]):
            return "yasl"
        # Kuroko indicators
        if indicators.contains_any_name([
            "kuroko.h", "kuroko.c", "kuroko"
        ]) or indicators.contains_any_content([
            r"\bKuroko\b"
        ]):
            return "kuroko"
        # Janet indicators
        if indicators.contains_any_name([
            "janet.h", "janet.c", "janet"
        ]) or indicators.contains_any_content([
            r"\bJanet\b", r"\bjanet_vm"
        ]):
            return "janet"
        # Lua indicators
        if indicators.contains_any_name([
            "lua.h", "luaconf.h", "lapi.c", "lvm.c", "lua"
        ]) or indicators.contains_any_content([
            r"\bLUA_", r"\blua_"
        ]):
            return "lua"
        # Wren indicators
        if indicators.contains_any_name([
            "wren.h", "wren_vm.c", "wren"
        ]) or indicators.contains_any_content([
            r"\bWren\b"
        ]):
            return "wren"
        # Python-like (Kuroko/Python)
        if indicators.contains_any_content([r"\bPyObject\b", r"\bPython\b"]):
            return "python"
        # PHP indicators
        if indicators.contains_any_name([
            "zend_execute.c", "php.h", "Zend", "php-src"
        ]) or indicators.contains_any_content([
            r"\bZEND_", r"\bzend_", r"\bPHP_\w+"
        ]):
            return "php"
        # JavaScript engines
        if indicators.contains_any_name([
            "quickjs.h", "quickjs", "duktape.h", "mujs.h", "jerryscript.h", "jsvalue.h"
        ]) or indicators.contains_any_content([
            r"\bJSValue\b", r"\bduk_", r"\bJSContext\b"
        ]):
            if indicators.contains_any_name(["quickjs", "quickjs.h"]):
                return "quickjs"
            if indicators.contains_any_name(["duktape.h"]):
                return "duktape"
            if indicators.contains_any_name(["mujs.h", "mujs"]):
                return "mujs"
            return "javascript"
        # YARA indicators
        if indicators.contains_any_name(["yara.h", "libyara"]) or indicators.contains_any_content([r"\bYR_RULE\b"]):
            return "yara"
        return "mruby"


class _Indicators:
    def __init__(self):
        self.fnames: List[str] = []
        self.sample_contents: List[Tuple[str, str]] = []  # (path, content)

    def contains_any_name(self, names: List[str]) -> bool:
        nset = set(n.lower() for n in self.fnames)
        for name in names:
            q = name.lower()
            for n in nset:
                if q in n:
                    return True
        return False

    def contains_any_content(self, patterns: List[str]) -> bool:
        for _, content in self.sample_contents:
            for pat in patterns:
                if re.search(pat, content):
                    return True
        return False


    def add_file(self, path: str, content: str):
        self.fnames.append(path)
        if len(self.sample_contents) < 200:
            # limit sampling to avoid memory blowup
            self.sample_contents.append((path, content[:50000]))


    def __repr__(self):
        return f"Indicators(names={len(self.fnames)}, samples={len(self.sample_contents)})"


    @staticmethod
    def from_path(src_path: str) -> "._Indicators":
        inst = _Indicators()
        for root, _, files in os.walk(src_path):
            for fn in files:
                p = os.path.join(root, fn)
                inst.fnames.append(p)
                if len(inst.sample_contents) < 200 and fn.endswith(('.c', '.h', '.cpp', '.hpp', '.txt', '.md', '.mk', '.y', '.l', '.py')):
                    try:
                        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                            inst.sample_contents.append((p, f.read(50000)))
                    except Exception:
                        pass
        return inst


    # compatibility alias
    def add(self, path: str, content: str):
        self.add_file(path, content)


    # expose for Solution._detect_project
    def __getattr__(self, item):
        # allow Solution to call functions names used
        raise AttributeError(item)


# helper to construct indicators object via function
def _scan_indicators_impl(src_path: str) -> _Indicators:
    return _Indicators.from_path(src_path)


# bind method in Solution
setattr(Solution, "_scan_indicators", staticmethod(_scan_indicators_impl))

# provide wrapper to keep naming aligned within Solution
def _scan_indicators_wrapper(self, src_path: str) -> _Indicators:
    return _scan_indicators_impl(src_path)

setattr(Solution, "_scan_indicators", _scan_indicators_wrapper)

# Patch Solution._detect_project to use indicators consistently
def _detect_project_impl(self, src_path: str) -> str:
    indicators = _Indicators.from_path(src_path)
    # Heuristic project detection from source files
    # mruby indicators
    if indicators.contains_any_name([
        "mruby.h", "mrbconf.h", "mruby", "include/mruby.h", "src/vm.c", "src/opcode.h", "mrb_"
    ]) or indicators.contains_any_content([
        r"\bmrb_", r"\bMRB_", r"ZeroDivisionError", r"MRB_TT_"
    ]):
        return "mruby"
    # Berry indicators
    if indicators.contains_any_name([
        "berry.h", "be_api.h", "be_vm.c", "be_exec.c", "berry"
    ]) or indicators.contains_any_content([
        r"\bbe_\w+", r"\bBE_", r"berry programming language"
    ]):
        return "berry"
    # YASL indicators
    if indicators.contains_any_name([
        "yasl.h", "YASL", "yasl-"
    ]) or indicators.contains_any_content([
        r"\bYASL\b", r"Yet Another Scripting Language"
    ]):
        return "yasl"
    # Kuroko indicators
    if indicators.contains_any_name([
        "kuroko.h", "kuroko.c", "kuroko"
    ]) or indicators.contains_any_content([
        r"\bKuroko\b"
    ]):
        return "kuroko"
    # Janet indicators
    if indicators.contains_any_name([
        "janet.h", "janet.c", "janet"
    ]) or indicators.contains_any_content([
        r"\bJanet\b", r"\bjanet_vm"
    ]):
        return "janet"
    # Lua indicators
    if indicators.contains_any_name([
        "lua.h", "luaconf.h", "lapi.c", "lvm.c", "lua"
    ]) or indicators.contains_any_content([
        r"\bLUA_", r"\blua_"
    ]):
        return "lua"
    # Wren indicators
    if indicators.contains_any_name([
        "wren.h", "wren_vm.c", "wren"
    ]) or indicators.contains_any_content([
        r"\bWren\b"
    ]):
        return "wren"
    # Python-like (Kuroko/Python)
    if indicators.contains_any_content([r"\bPyObject\b", r"\bPython\b"]):
        return "python"
    # PHP indicators
    if indicators.contains_any_name([
        "zend_execute.c", "php.h", "Zend", "php-src"
    ]) or indicators.contains_any_content([
        r"\bZEND_", r"\bzend_", r"\bPHP_\w+"
    ]):
        return "php"
    # JavaScript engines
    if indicators.contains_any_name([
        "quickjs.h", "quickjs", "duktape.h", "mujs.h", "jerryscript.h", "jsvalue.h"
    ]) or indicators.contains_any_content([
        r"\bJSValue\b", r"\bduk_", r"\bJSContext\b"
    ]):
        if indicators.contains_any_name(["quickjs", "quickjs.h"]):
            return "quickjs"
        if indicators.contains_any_name(["duktape.h"]):
            return "duktape"
        if indicators.contains_any_name(["mujs.h", "mujs"]):
            return "mujs"
        return "javascript"
    # YARA indicators
    if indicators.contains_any_name(["yara.h", "libyara"]) or indicators.contains_any_content([r"\bYR_RULE\b"]):
        return "yara"
    return "mruby"

setattr(Solution, "_detect_project", _detect_project_impl)