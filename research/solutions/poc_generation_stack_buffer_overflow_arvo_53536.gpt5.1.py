import tarfile
import re
import collections


class Solution:
    def solve(self, src_path: str) -> bytes:
        delim_open_candidates = set()
        delim_close_candidates = set()
        string_literals = []
        simple_word_counter = collections.Counter()

        string_re = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
        char_re = re.compile(r"'([^'\\]*(?:\\.[^'\\]*)*)'")

        tf = None
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            tf = None

        if tf is not None:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name.lower()
                if not (name.endswith(".c") or name.endswith(".h") or name.endswith(".cpp")
                        or name.endswith(".cc") or name.endswith(".hpp") or name.endswith(".cxx")
                        or name.endswith(".hh") or name.endswith(".hxx")):
                    continue
                f = tf.extractfile(m)
                if f is None:
                    continue
                try:
                    data_bytes = f.read()
                except Exception:
                    continue
                if not data_bytes:
                    continue
                try:
                    text = data_bytes.decode("utf-8", errors="ignore")
                except Exception:
                    continue

                for sm in string_re.finditer(text):
                    s = sm.group(1)
                    try:
                        s_unescaped = bytes(s, "utf-8").decode("unicode_escape", errors="ignore")
                    except Exception:
                        s_unescaped = s
                    string_literals.append(s_unescaped)
                    if 1 <= len(s_unescaped) <= 16 and s_unescaped.isalpha():
                        simple_word_counter[s_unescaped] += 1

                for cm in char_re.finditer(text):
                    c = cm.group(1)
                    if not c:
                        continue
                    if c.startswith("\\"):
                        if len(c) >= 2:
                            esc = c[1]
                            mapping = {
                                "n": "\n",
                                "t": "\t",
                                "r": "\r",
                                "0": "\0",
                                "'": "'",
                                '"': '"',
                                "\\": "\\",
                            }
                            ch = mapping.get(esc)
                            if ch is None:
                                continue
                        else:
                            continue
                    else:
                        ch = c[0]
                    if ch in "<[{(@":
                        delim_open_candidates.add(ch)
                    if ch in ">]})@":
                        delim_close_candidates.add(ch)
            tf.close()

        delim_pairs = []
        if '<' in delim_open_candidates and '>' in delim_close_candidates:
            delim_pairs.append(('<', '>'))
        if '[' in delim_open_candidates and ']' in delim_close_candidates:
            delim_pairs.append('[', ']')
        if '{' in delim_open_candidates and '}' in delim_close_candidates:
            delim_pairs.append('{', '}')
        if '(' in delim_open_candidates and ')' in delim_close_candidates:
            delim_pairs.append('(', ')')
        if '@' in delim_open_candidates and '@' in delim_close_candidates:
            delim_pairs.append('@', '@')
        if not delim_pairs:
            delim_pairs.append(('<', '>'))

        default_names = ["TAG", "tag", "b", "i"]
        for word, _cnt in simple_word_counter.most_common(10):
            default_names.append(word)
        seen = set()
        tag_names = []
        for n in default_names:
            if n not in seen:
                seen.add(n)
                tag_names.append(n)
        if not tag_names:
            tag_names = ["TAG"]
        else:
            tag_names = tag_names[:6]

        explicit_tags = set()
        for s in string_literals:
            for oc, cc in delim_pairs:
                if s.startswith(oc) and s.endswith(cc) and len(s) >= 3:
                    explicit_tags.add(s)

        parts = []
        parts.append("START\n")
        inner_text = "X" * 16
        for open_c, close_c in delim_pairs:
            for name in tag_names:
                open_tag = open_c + name + close_c
                close_tag = open_c + "/" + name + close_c
                parts.append(open_tag + inner_text + close_tag)
                parts.append(open_tag)
                parts.append(close_tag)
                parts.append(open_tag + open_tag + inner_text + close_tag + close_tag)

        for t in explicit_tags:
            parts.append(t)
            if len(t) > 2 and not (len(t) >= 2 and t[1] == '/'):
                oc = t[0]
                cc = t[-1]
                inner = t[1:-1]
                parts.append(oc + "/" + inner + cc)

        base_pattern = "".join(parts)
        if not base_pattern:
            base_pattern = "<TAG>XXXX</TAG>"

        target_len = 20000
        repetitions = max(1, target_len // max(1, len(base_pattern)) + 1)
        big_body = base_pattern * repetitions
        poc_str = big_body + "\nEND\n"

        return poc_str.encode("utf-8")
