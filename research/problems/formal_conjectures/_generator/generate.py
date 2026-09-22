#!/usr/bin/env python3
"""
Generate one Frontier-CS research problem per formal-conjectures statement,
directly from the third_party/formal-conjectures submodule sources.

Each theorem tagged `@[category research open]` or `@[category research solved]`
becomes a problem directory:

    research/problems/formal_conjectures/<source>/<TheoremName>/
        config.yaml    # identical for all problems
        evaluate.sh    # identical (in-container entrypoint)
        check.sh       # host-side wrapper: ./check.sh solution.lean scores locally
        evaluator.py   # thin shim importing ../../common/fc_evaluator.py
        target.json    # which module/theorem this problem targets
        readme         # statement, docstring, submission contract

Generated directories are NOT committed (see ../.gitignore): the submodule is
the source of truth and generation is deterministic. Run this script once per
checkout (and after every submodule bump):

    python3 research/problems/formal_conjectures/_generator/generate.py --wipe

"Fill-in-the-answer" conjectures — statements using `answer(sorry)` for an
unknown answer — get special treatment. Upstream's `answer()` elaborator
substitutes a placeholder (`True` for Props), so their elaborated type
misstates the question and the plain "prove this statement" contract would be
unsound. Statements of the exact shape `theorem n : answer(sorry) ↔ Q` become
mode "prove_or_disprove" problems instead (target.json `mode` field): the task
is to prove `Q` or `¬Q`, checked by the trusted driver against the compiled
`True ↔ Q` type. All other answer-style statements (value-style answers,
ambiguous shapes, statements referencing same-file sorry-defs) remain
excluded rather than misrepresented — there is no sound automatic check for
"is this value a genuine answer".

The parser can be cross-checked against the upstream extractor (ground truth
from the built Lean environment):

    docker run --rm <eval-image> lake exe extract_names > /tmp/extract.json
    python3 generate.py --check-against /tmp/extract.json
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

GENERATOR_DIR = Path(__file__).resolve().parent
PROBLEMS_ROOT = GENERATOR_DIR.parent          # research/problems/formal_conjectures
REPO_ROOT = PROBLEMS_ROOT.parents[2]
SUBMODULE = REPO_ROOT / "third_party" / "formal-conjectures"
UPSTREAM = "https://github.com/google-deepmind/formal-conjectures"

DEFAULT_CATEGORIES = ("research open", "research solved")
IMAGE = "shangyint/formal-conjectures-eval"

CONFIG_YAML = """\
tag: math
runtime:
  language: lean
  timeout_seconds: 1800
  environment: "Lean 4 + Mathlib + formal-conjectures ({ref}), prebuilt at /opt/formal-conjectures"
  docker:
    image: {image}:{ref}
  resources:
    cpus: "8"
    memory: "32"
"""

EVALUATE_SH = """\
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
# Default is the harness layout; override for standalone runs inside the eval
# image (or just use ./check.sh from the host, which sets this for you).
SOLUTION_PATH="${SOLUTION_PATH:-/work/execution_env/solution_env/solution.lean}"
python3 evaluator.py --solution-path "$SOLUTION_PATH" --target target.json
"""

# Host-side scorer; @IMAGE_REF@ is substituted at generation time (the template
# is .replace()d, not .format()ted, because of the bash ${...} braces).
CHECK_SH = """\
#!/usr/bin/env bash
# Score a candidate solution for this problem locally. Requires docker and the
# prebuilt eval image. Prints evaluator diagnostics on stderr; the last stdout
# line is the score (1.0 accepted / 0.0 rejected). Takes ~2 min (import loading).
#
#   ./check.sh path/to/solution.lean
set -euo pipefail
if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
  echo "usage: $0 path/to/solution.lean" >&2
  exit 2
fi
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
FC_ROOT=$(cd "$SCRIPT_DIR/../.." && pwd)
REL=${SCRIPT_DIR#"$FC_ROOT"/}
SOLUTION=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
exec docker run --rm \\
  -v "$FC_ROOT":/fcp:ro \\
  -v "$SOLUTION":/sol/solution.lean:ro \\
  -e SOLUTION_PATH=/sol/solution.lean \\
  @IMAGE_REF@ \\
  bash "/fcp/$REL/evaluate.sh"
"""

EVALUATOR_PY = """\
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "common"))

from fc_evaluator import main

if __name__ == "__main__":
    main()
"""

README = """\
# {theorem}

Formalized conjecture from [google-deepmind/formal-conjectures]({upstream}) at
`{ref}` — source: [`{source_file}`]({upstream}/blob/{ref}/{source_file})
(vendored at `third_party/formal-conjectures`; Apache-2.0 / CC-BY).

- Category: {category}
- AMS subjects: {subjects}

## Statement
{docstring_section}
```lean
{statement} := by
  sorry
```
{namespace_note}
## Task

Prove this statement. Submit **one Lean 4 file** that:

1. Imports the module containing the statement (plus anything else you need
   from Mathlib):

   ```lean
   import {module_dotted}
   ```

2. Declares a **top-level** theorem named `solution` whose statement is
   *exactly* the statement above (you may `open` the relevant namespaces, or
   restate it in any definitionally equal form):

   ```lean
   theorem solution : <statement> := <your proof>
   ```

## Scoring

Binary. Score 1.0 iff:

- the file compiles against Lean {lean_version} + Mathlib + formal-conjectures
  `{ref}` (the exact prebuilt environment is in the evaluation image),
- it contains no `sorry` / `admit`,
- the type of `solution` is definitionally equal to the statement of
  `{theorem}`, and
- `solution` depends on no axioms beyond `propext`, `Classical.choice`,
  `Quot.sound`.

Anything else scores 0.0. Not allowed (rejected by lint): `axiom`, `macro`,
`elab`, `syntax`, `notation`, `initialize`, `run_cmd`, `implemented_by`,
`extern`, `unsafe`, `native_decide`, `set_option debug.*`.

## Local verification

With docker available, score a candidate from this problem directory:

    ./check.sh path/to/solution.lean

This runs the official evaluator (lint + compile + trusted statement/axiom
check) inside `{image_ref}`; the last stdout line is the score. A run takes
~2 minutes, almost all of it Mathlib import loading — so while iterating,
prefer one compile-only pass over many small ones, batching experimental
lemmas into a single file:

    docker run --rm -v "$PWD":/sol {image_ref} \\
      bash -c 'cd /opt/formal-conjectures && lake env lean --root /sol /sol/solution.lean'

Exit code 0 with no output means it compiles (`sorry` still compiles, with a
warning). Mathlib and formal-conjectures sources are browsable in the image
under `/opt/formal-conjectures`.
"""


README_POD = """\
# {theorem}

Formalized fill-in-the-answer conjecture from
[google-deepmind/formal-conjectures]({upstream}) at
`{ref}` — source: [`{source_file}`]({upstream}/blob/{ref}/{source_file})
(vendored at `third_party/formal-conjectures`; Apache-2.0 / CC-BY).

- Category: {category}
- AMS subjects: {subjects}
- Mode: prove or disprove

## Statement
{docstring_section}
The upstream statement leaves its truth value open — `answer(sorry)` marks
the unknown answer:

```lean
{statement} := by
  sorry
```

The question, `Q`, is the right-hand side of the iff:

```lean
Q := {question}
```

(In the prebuilt environment the `answer(sorry)` placeholder elaborates to
`True`, so the declared statement reads `True ↔ Q`. Do **not** prove that —
it misstates the question and scores 0.0.)
{namespace_note}
## Task

Determine whether `Q` is true or false, and prove your answer. Submit **one
Lean 4 file** that:

1. Imports the module containing the statement (plus anything else you need
   from Mathlib):

   ```lean
   import {module_dotted}
   ```

2. Declares a **top-level** theorem named `solution` proving either `Q` or
   `¬Q` (you may `open` the relevant namespaces, or use any definitionally
   equal form):

   ```lean
   theorem solution : <Q> := <your proof>       -- claiming the answer is yes
   -- or
   theorem solution : ¬(<Q>) := <your proof>    -- claiming the answer is no
   ```

## Scoring

Binary. Score 1.0 iff:

- the file compiles against Lean {lean_version} + Mathlib + formal-conjectures
  `{ref}` (the exact prebuilt environment is in the evaluation image),
- it contains no `sorry` / `admit`,
- the type of `solution` is definitionally equal to `Q` or to `¬Q`, where the
  trusted checker extracts `Q` from the compiled statement of `{theorem}`, and
- `solution` depends on no axioms beyond `propext`, `Classical.choice`,
  `Quot.sound`.

Anything else — including anything the trusted checker cannot positively
verify — scores 0.0. Not allowed (rejected by lint): `axiom`, `macro`,
`elab`, `syntax`, `notation`, `initialize`, `run_cmd`, `implemented_by`,
`extern`, `unsafe`, `native_decide`, `set_option debug.*`.

## Local verification

With docker available, score a candidate from this problem directory:

    ./check.sh path/to/solution.lean

This runs the official evaluator (lint + compile + trusted statement/axiom
check) inside `{image_ref}`; the last stdout line is the score. A run takes
~2 minutes, almost all of it Mathlib import loading — so while iterating,
prefer one compile-only pass over many small ones, batching experimental
lemmas into a single file:

    docker run --rm -v "$PWD":/sol {image_ref} \\
      bash -c 'cd /opt/formal-conjectures && lake env lean --root /sol /sol/solution.lean'

Exit code 0 with no output means it compiles (`sorry` still compiles, with a
warning). Mathlib and formal-conjectures sources are browsable in the image
under `/opt/formal-conjectures`.
"""


# --------------------------------------------------------------------------
# Lean source parsing
# --------------------------------------------------------------------------

# Exact fill-in-the-answer shape rescuable as prove-or-disprove: the statement
# is a binder-free top-level `answer(sorry) ↔ Q`. (Trailing `Q ↔ answer(sorry)`
# is textually ambiguous with `∀ x, (P x ↔ answer(sorry))` and is not rescued.)
ANSWER_IFF_RE = re.compile(
    r"(?s)\b(?:theorem|lemma)\s+[^\s:({\[⦃⟨]+\s*:\s*"
    r"answer\(\s*sorry\s*\)\s*↔\s*(.+)$"
)

DECL_RE = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+)*(?:theorem|lemma)\s+"
    r"([^\s:({\[⦃⟨]+)"
)
DEF_RE = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+)*(?:def|abbrev)\s+"
    r"([^\s:({\[⦃⟨]+)"
)
ANON_INSTANCE_RE = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+)*instance\b"
)
NAMESPACE_RE = re.compile(r"^namespace\s+(\S+)")
SECTION_RE = re.compile(r"^(?:noncomputable\s+)?section\b")
END_RE = re.compile(r"^end\b")
VARIABLE_RE = re.compile(r"^variables?\b")
OPEN_BRACKETS = "([{⟨⦃"
CLOSE_BRACKETS = ")]}⟩⦄"


@dataclass
class Decl:
    full_name_components: list
    category: str
    subjects: list
    statement: str          # attr line(s) + signature, proof stripped
    docstring: str
    module_components: list
    source_file: str
    skip_answer_style: bool
    answer_taint: bool = False  # statement references same-file sorry-defs
    uses_section_vars: bool = False  # statement references in-scope `variable`s

    @property
    def full_name(self) -> str:
        return ".".join(self.full_name_components)


def split_name(dotted: str) -> list:
    """Split a Lean dotted name into components, honoring «...» quoting."""
    components, buf, depth = [], [], 0
    for ch in dotted:
        if ch == "«":
            depth += 1
        elif ch == "»":
            depth -= 1
        elif ch == "." and depth == 0:
            components.append("".join(buf))
            buf = []
            continue
        else:
            buf.append(ch)
    components.append("".join(buf))
    return components


def is_internal(components: list) -> bool:
    """Mirror upstream extract_names: names with `_`/`match_`/`proof_`-prefixed
    components are auxiliary declarations, not benchmark statements."""
    return any(c.startswith(("_", "match_", "proof_")) for c in components)


def snake(name: str) -> str:
    """CamelCase source dir -> snake_case problem dir (ErdosProblems -> erdos_problems)."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name)
    return s.lower()


def sanitize(component: str) -> str:
    return re.sub(r"[^A-Za-z0-9_']", "_", component)


def consume_block_comment(s: str, depth: int):
    """Consume a (nesting) block comment. Returns (remainder, new_depth)."""
    pos = 0
    while depth > 0:
        opener = s.find("/-", pos)
        closer = s.find("-/", pos)
        if opener != -1 and (closer == -1 or opener < closer):
            depth += 1
            pos = opener + 2
        elif closer != -1:
            depth -= 1
            pos = closer + 2
        else:
            return "", depth
    return s[pos:], 0


class LineCleaner:
    """Strips comments from source lines while capturing docstrings, across
    lines. Feed raw lines; get back the code content of each line."""

    def __init__(self):
        self.comment_depth = 0
        self.docstring_open = None      # accumulating /-- ... -/ lines
        self.last_docstring = ""

    def feed(self, raw: str) -> str:
        s = raw
        if self.docstring_open is not None:
            if "-/" not in s:
                self.docstring_open.append(raw)
                return ""
            before, s = s.split("-/", 1)
            self.docstring_open.append(before)
            self.last_docstring = "\n".join(self.docstring_open).strip()
            self.docstring_open = None
        if self.comment_depth > 0:
            s, self.comment_depth = consume_block_comment(s, self.comment_depth)
            if self.comment_depth > 0:
                return ""

        out = []
        j = 0
        while j < len(s):
            if s[j : j + 2] == "--":
                break
            if s[j : j + 3] == "/--":
                end = s.find("-/", j + 3)
                if end == -1:
                    self.docstring_open = [s[j + 3 :]]
                    break
                self.last_docstring = s[j + 3 : end].strip()
                j = end + 2
                continue
            if s[j : j + 2] == "/-":
                rest, self.comment_depth = consume_block_comment(s[j + 2 :], 1)
                if self.comment_depth > 0:
                    break
                s = rest
                j = 0
                continue
            out.append(s[j])
            j += 1
        return "".join(out)


def clean_lines(text: str):
    """Return (code_lines, docstring_before_line) for a Lean source text."""
    cleaner = LineCleaner()
    code_lines, doc_map = [], []
    for raw in text.split("\n"):
        doc_map.append(cleaner.last_docstring)
        code_lines.append(cleaner.feed(raw))
    return code_lines, doc_map


def capture_statement(code_lines: list, start: int) -> str:
    """Capture a declaration's signature from `code_lines[start]` up to
    (excluding) the first `:=` at bracket depth 0. Note: `let x := e` inside a
    statement type will truncate the capture early — acceptable, the capture is
    for display only and the readme links to the full source."""
    captured, depth = [], 0
    for code in code_lines[start : start + 80]:
        i = 0
        while i < len(code):
            ch = code[i]
            if ch in OPEN_BRACKETS:
                depth += 1
            elif ch in CLOSE_BRACKETS:
                depth -= 1
            elif ch == ":" and depth == 0 and code[i : i + 2] == ":=":
                captured.append(code[:i].rstrip())
                return "\n".join(c for c in captured if c.strip()).rstrip()
            i += 1
        captured.append(code.rstrip())
    return "\n".join(c for c in captured if c.strip()).rstrip()


def capture_decl_text(code_lines: list, start: int) -> str:
    """Full text of a top-level declaration: from its first line until the next
    column-0 code line (or EOF)."""
    chunk = [code_lines[start]]
    for code in code_lines[start + 1 :]:
        if code and not code[0].isspace():
            break
        chunk.append(code)
    return "\n".join(chunk)


def parse_attr_list(attr_text: str) -> list:
    """Split the inside of an @[...] block on top-level commas."""
    parts, buf, depth = [], [], 0
    for ch in attr_text:
        if ch in OPEN_BRACKETS:
            depth += 1
        elif ch in CLOSE_BRACKETS:
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def extract_binder_names(text: str) -> list:
    """Names bound by a `variable ...` declaration: for each top-level binder
    group, the identifiers before its `:`. Groups with no `:` (anonymous
    instance binders like `[Fintype V]`) bind no names."""
    text = re.sub(r"^\s*variables?\b", "", text.strip())
    names, depth, buf = [], 0, None
    for ch in text:
        if ch in OPEN_BRACKETS:
            depth += 1
            if depth == 1:
                buf = []
                continue
        elif ch in CLOSE_BRACKETS:
            depth -= 1
            if depth == 0:
                buf = None
            continue
        if depth == 1 and buf is not None:
            if ch == ":":
                names += "".join(buf).split()
                buf = None
            else:
                buf.append(ch)
    return [n for n in names if re.fullmatch(r"[^\W\d][\w']*", n)]


def find_tainted_defs(code_lines: list) -> set:
    """Names of same-file `def`/`abbrev` declarations whose body contains
    `answer(` or `sorry` — statements referencing them are fill-in-the-answer
    style (their elaborated type embeds a placeholder)."""
    tainted = set()
    for idx, code in enumerate(code_lines):
        stripped = code.strip()
        m = DEF_RE.match(stripped)
        if not m:
            continue
        body = capture_decl_text(code_lines, idx)
        if re.search(r"\banswer\(|\bsorry\b", body):
            tainted.add(split_name(m.group(1))[-1])
    return tainted


def parse_lean_file(path: Path, submodule: Path) -> list:
    """Extract categorized theorem declarations from one Lean source file."""
    rel = path.relative_to(submodule)
    module_components = list(rel.with_suffix("").parts)
    source_file = str(rel)
    text = path.read_text(encoding="utf-8")
    code_lines, doc_map = clean_lines(text)
    tainted = find_tainted_defs(code_lines)

    decls = []
    scope = []                  # ("ns", [components]) | ("sec", None)
    var_stack = [[]]            # variable names bound per scope frame
    pending_attrs = []          # accumulated @[...] attribute strings
    pending_doc = ""
    attr_buf = None             # multi-line @[...] accumulator

    for idx, code_raw in enumerate(code_lines):
        code = code_raw.strip()
        if not code:
            continue

        if attr_buf is not None:
            attr_buf.append(code)
            joined = " ".join(attr_buf)
            if joined.count("[") == joined.count("]"):
                pending_attrs.append(joined)
                attr_buf = None
            continue
        if code.startswith("@["):
            pending_doc = doc_map[idx]
            if code.count("[") == code.count("]"):
                pending_attrs.append(code)
                after = code[code.rindex("]") + 1 :].strip()
                if not after:
                    continue
                code = after        # attribute and declaration on one line
            else:
                attr_buf = [code]
                continue

        m = NAMESPACE_RE.match(code)
        if m:
            scope.append(("ns", split_name(m.group(1))))
            var_stack.append([])
            pending_attrs = []
            continue
        if SECTION_RE.match(code):
            scope.append(("sec", None))
            var_stack.append([])
            pending_attrs = []
            continue
        if END_RE.match(code):
            if scope:
                scope.pop()
            if len(var_stack) > 1:
                var_stack.pop()
            pending_attrs = []
            continue
        if VARIABLE_RE.match(code):
            var_stack[-1].extend(
                extract_binder_names(capture_decl_text(code_lines, idx)))
            pending_attrs = []
            continue

        m = DECL_RE.match(code)
        if m:
            category, subjects, attr_display = None, [], []
            for attr in pending_attrs:
                inner = attr.strip()
                if inner.startswith("@[") and inner.endswith("]"):
                    inner = inner[2:-1]
                for part in parse_attr_list(inner):
                    cm = re.match(r"category\s+(research\s+(?:open|solved)|test|API|textbook)", part)
                    if cm:
                        category = re.sub(r"\s+", " ", cm.group(1))
                        attr_display.append(part)
                    am = re.match(r"AMS((?:\s+\d+)+)$", part)
                    if am:
                        subjects = am.group(1).split()
                        attr_display.append(part)
            if category is not None:
                ns_components = [c for kind, comps in scope if kind == "ns" for c in comps]
                name_components = ns_components + split_name(m.group(1))
                if is_internal(name_components):
                    pending_attrs = []
                    continue
                statement_body = capture_statement(code_lines, idx)
                decl_text = capture_decl_text(code_lines, idx)
                taint = any(
                    re.search(rf"(?<![A-Za-z0-9_']){re.escape(t)}(?![A-Za-z0-9_'])",
                              statement_body)
                    for t in tainted
                )
                answer_style = taint or bool(
                    re.search(r"\banswer\(\s*[^)]*\bsorry\b", decl_text)
                )
                stmt_tokens = set(re.findall(r"[^\W\d][\w']*", statement_body))
                uses_vars = any(
                    v in stmt_tokens for frame in var_stack for v in frame)
                statement = ("@[" + ", ".join(attr_display) + "]\n" if attr_display else "") \
                    + statement_body
                decls.append(Decl(
                    full_name_components=name_components,
                    category=category,
                    subjects=subjects,
                    statement=statement,
                    docstring=doc_map[idx] if doc_map[idx] else pending_doc,
                    module_components=module_components,
                    source_file=source_file,
                    skip_answer_style=answer_style,
                    answer_taint=taint,
                    uses_section_vars=uses_vars,
                ))
            pending_attrs = []
            continue

        if ANON_INSTANCE_RE.match(code) and any(
            "category research" in a for a in pending_attrs
        ):
            print(f"WARNING: {source_file}:{idx + 1}: anonymous `instance` with a "
                  "research category attribute cannot be targeted by name; skipped",
                  file=sys.stderr)

        pending_attrs = []

    return decls


def parse_all(submodule: Path) -> list:
    decls = []
    for lean_file in sorted((submodule / "FormalConjectures").rglob("*.lean")):
        decls.extend(parse_lean_file(lean_file, submodule))
    return decls


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def answer_iff_question(decl: Decl):
    """Textual `Q` for fill-in-the-answer statements of the exact rescuable
    shape `theorem <name> : answer(sorry) ↔ Q` — binder-free, exactly one
    `answer()`/`sorry`, and no same-file sorry-def references. None otherwise.

    This gate is presentation-side only; the trusted checker independently
    verifies the compiled statement has the `True ↔ Q` placeholder shape and
    fails closed (0.0) on anything it cannot positively verify.

    Statements referencing section `variable`s are not rescuable: the compiled
    type gains leading ∀ binders (`∀ vars, True ↔ Q`), which both breaks the
    top-level-iff shape and makes prove-or-disprove semantically ambiguous
    (the answer could differ per instantiation). Validate any change here with
    _generator/shape_check.sh, which checks every generated prove-or-disprove
    target's compiled type in the eval image.
    """
    if decl.answer_taint or decl.uses_section_vars:
        return None
    if decl.statement.count("answer(") != 1:
        return None
    if len(re.findall(r"\bsorry\b", decl.statement)) != 1:
        return None
    m = ANSWER_IFF_RE.search(decl.statement)
    if not m:
        return None
    return m.group(1).strip()


def generate(decls: list, out: Path, ref: str, lean_version: str,
             categories: set, only: str) -> None:
    generated, skipped_answer, by_category = [], [], {}
    n_pod = 0
    seen_dirs = set()

    for decl in sorted(decls, key=lambda d: (d.source_file, d.full_name)):
        if only:
            if decl.full_name != only:
                continue
        elif decl.category not in categories:
            continue

        question = None
        if decl.skip_answer_style:
            question = answer_iff_question(decl)
            if question is None:
                skipped_answer.append(decl.full_name)
                continue

        source = snake(decl.module_components[1]) if len(decl.module_components) > 1 else "misc"
        dir_name = ".".join(sanitize(c) for c in decl.full_name_components)
        problem_dir = out / source / dir_name

        if str(problem_dir) in seen_dirs:
            print(f"WARNING: duplicate problem dir {problem_dir}, skipping {decl.full_name}",
                  file=sys.stderr)
            continue
        seen_dirs.add(str(problem_dir))

        module_dotted = ".".join(
            c if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_']*", c) else f"«{c}»"
            for c in decl.module_components
        )
        namespace_note = ""
        if len(decl.full_name_components) > 1:
            ns_prefix = decl.full_name_components[0]
            namespace_note = (
                f"\nThe statement lives in namespace `{ns_prefix}` "
                f"(fully-qualified name: `{decl.full_name}`); "
                f"`open {ns_prefix} in` may be convenient.\n"
            )

        docstring_section = f"\n{decl.docstring}\n" if decl.docstring else ""

        problem_dir.mkdir(parents=True, exist_ok=True)
        (problem_dir / "config.yaml").write_text(
            CONFIG_YAML.format(ref=ref, image=IMAGE), encoding="utf-8")
        (problem_dir / "evaluate.sh").write_text(EVALUATE_SH, encoding="utf-8")
        (problem_dir / "check.sh").write_text(
            CHECK_SH.replace("@IMAGE_REF@", f"{IMAGE}:{ref}"), encoding="utf-8")
        (problem_dir / "evaluator.py").write_text(EVALUATOR_PY, encoding="utf-8")
        target = {
            "module": decl.module_components,
            "theorem": decl.full_name_components,
            "category": decl.category,
            "subjects": decl.subjects,
            "source_file": decl.source_file,
            "ref": ref,
        }
        if question is not None:
            target["mode"] = "prove_or_disprove"
        (problem_dir / "target.json").write_text(
            json.dumps(target, indent=2) + "\n", encoding="utf-8",
        )
        readme_kwargs = dict(
            theorem=decl.full_name,
            upstream=UPSTREAM,
            ref=ref,
            source_file=decl.source_file,
            category=decl.category,
            subjects=", ".join(decl.subjects) or "-",
            statement=decl.statement,
            docstring_section=docstring_section,
            namespace_note=namespace_note,
            module_dotted=module_dotted,
            lean_version=lean_version,
            image_ref=f"{IMAGE}:{ref}",
        )
        if question is None:
            readme = README.format(**readme_kwargs)
        else:
            readme = README_POD.format(question=question, **readme_kwargs)
            n_pod += 1
        (problem_dir / "readme").write_text(readme, encoding="utf-8")
        (problem_dir / "evaluate.sh").chmod(0o755)
        (problem_dir / "check.sh").chmod(0o755)

        generated.append(decl.full_name)
        by_category[decl.category] = by_category.get(decl.category, 0) + 1

    print(f"generated {len(generated)} problems into {out} "
          f"({len(generated) - n_pod} prove, {n_pod} prove-or-disprove)")
    for cat, n in sorted(by_category.items()):
        print(f"  {cat}: {n}")
    print(f"skipped {len(skipped_answer)} answer-style statements with no sound "
          "check mode (value-style, ambiguous shape, or sorry-def taint)")


def check_against(decls: list, extractor_json: Path, categories: set) -> int:
    """Diff the parser's output against `lake exe extract_names` ground truth.

    Pass criteria:
      - the (name, category) sets agree, except for warned anonymous instances
        that appear only on the extractor side;
      - every statement whose *elaborated type* contains sorry per the
        extractor is also skipped by the parser (the parser intentionally
        skips MORE: `answer(sorry)` Props elaborate to a `True` placeholder
        that the extractor cannot distinguish from a real statement).
    """
    data = json.loads(extractor_json.read_text(encoding="utf-8"))
    entries = data["problems"] if isinstance(data, dict) else data

    def norm(name: str) -> str:
        return ".".join(split_name(name))

    truth = {norm(e["theorem"]): e["category"] for e in entries
             if e["category"] in categories}
    mine = {d.full_name: d.category for d in decls if d.category in categories}

    missing = sorted(set(truth) - set(mine))
    extra = sorted(set(mine) - set(truth))
    miscat = sorted(n for n in set(truth) & set(mine) if truth[n] != mine[n])

    print(f"extractor: {len(truth)}  parser: {len(mine)}")
    for label, names in [("MISSING (in extractor, not parsed)", missing),
                         ("EXTRA (parsed, not in extractor)", extra),
                         ("CATEGORY MISMATCH", miscat)]:
        print(f"{label}: {len(names)}")
        for n in names[:20]:
            print(f"  - {n}")

    truth_sorry = {norm(e["theorem"]) for e in entries
                   if e["category"] in categories
                   and re.search(r"\bsorry(Ax)?\b", e.get("statement", ""))}
    mine_sorry = {d.full_name for d in decls
                  if d.category in categories and d.skip_answer_style}
    uncovered = sorted(truth_sorry - (mine_sorry | set(missing)))
    print(f"type-contains-sorry (extractor): {len(truth_sorry)}  "
          f"answer-style skipped (parser): {len(mine_sorry)}")
    print(f"UNCOVERED type-sorry statements (would become broken problems): "
          f"{len(uncovered)} {uncovered[:10]}")

    instance_only_missing = all("inst" in n.split(".")[-1] for n in missing)
    ok = (not extra and not miscat and not uncovered
          and (not missing or instance_only_missing))
    print("CHECK:", "OK" if ok else "FAILED")
    return 0 if ok else 1


def generation_stamp(submodule_head: str) -> str:
    """Stamp identifying what generated dirs were produced from. Must stay in
    sync with the reimplementation in src/frontier_cs/lazy_problems.py."""
    ghash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    return f"{submodule_head}+{ghash}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=PROBLEMS_ROOT,
                        help="Problems root to generate into")
    parser.add_argument("--ref", default=None,
                        help="formal-conjectures ref (default: submodule tag)")
    parser.add_argument("--categories", default=",".join(DEFAULT_CATEGORIES),
                        help="Comma-separated categories to include")
    parser.add_argument("--only", default=None,
                        help="Generate only this fully-qualified theorem (any category)")
    parser.add_argument("--wipe", action="store_true",
                        help="Remove previously generated source dirs first")
    parser.add_argument("--check-against", type=Path, default=None,
                        help="Diff parser output against extract_names JSON and exit")
    args = parser.parse_args()

    if not (SUBMODULE / "FormalConjectures").is_dir():
        print("ERROR: submodule not initialized. Run: git submodule update --init",
              file=sys.stderr)
        return 1

    decls = parse_all(SUBMODULE)
    categories = {c.strip() for c in args.categories.split(",")}

    if args.check_against:
        return check_against(decls, args.check_against, categories)

    if args.ref:
        ref = args.ref
    else:
        ref = subprocess.run(
            ["git", "-C", str(SUBMODULE), "describe", "--tags", "--exact-match"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    lean_version = (SUBMODULE / "lean-toolchain").read_text().strip().split(":")[-1]

    if args.wipe and not args.only:
        for child in args.out.iterdir():
            if child.is_dir() and child.name not in ("common", "docker", "_generator"):
                shutil.rmtree(child)

    generate(decls, args.out, ref, lean_version, categories, args.only)

    # Stamp submodule commit + generator hash so the framework's lazy
    # materialization (src/frontier_cs/lazy_problems.py) regenerates when
    # either the sources or the templates change.
    if not args.only and args.out == PROBLEMS_ROOT:
        head = subprocess.run(
            ["git", "-C", str(SUBMODULE), "rev-parse", "HEAD"],
            capture_output=True, text=True,
        )
        if head.returncode == 0:
            (GENERATOR_DIR / ".generated-ref").write_text(
                generation_stamp(head.stdout.strip()) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
