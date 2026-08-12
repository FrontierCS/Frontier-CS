"""Run the judge's exact static gate on a submission, locally.

Imports /app/policy.py -- the same module the judge uses -- rather than
restating the rules, so the two cannot drift apart.

This checks only what is checkable without a GPU: size, the required factory,
and the forbidden-token rules. It cannot tell you whether your architecture is
GOOD; only a scored submission does that.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec_module. policy.py defines a @dataclass, and
    # dataclasses resolves string annotations via sys.modules[cls.__module__];
    # if the module is absent from sys.modules that lookup returns None and the
    # decorator dies with "NoneType has no attribute __dict__". This is the
    # documented spec_from_file_location idiom, not a workaround.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    target = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/app/model.py")
    if not target.exists():
        print(f"FAIL  {target} does not exist")
        return 1

    policy = _load("policy", pathlib.Path("/app/policy.py"))
    src = target.read_text(encoding="utf-8", errors="replace")
    res = policy.check_source(src)

    print(f"file   : {target}  ({len(src.encode()):,} bytes)")
    print(f"policy : {'ok' if res.ok else 'REJECTED'}")
    if not res.ok:
        print(f"reason : {res.reason}")
        return 1

    # Cheap structural check the judge would otherwise charge a training run for.
    import ast
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        print(f"FAIL   does not parse: line {exc.lineno}")
        return 1
    names = {n.name for n in ast.walk(tree)
             if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    if "build_model" not in names and "NanoSLM" not in names:
        print("FAIL   must define build_model(config) or class NanoSLM")
        return 1

    print("RESULT : PASS (static only -- architecture quality is not checked here)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
