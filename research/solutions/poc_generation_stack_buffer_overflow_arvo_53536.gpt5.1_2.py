import tarfile
import re


class Solution:
    def _analyze_source(self, src_path):
        openers_map = {'<': '>', '[': ']', '{': '}', '(': ')'}
        found_tag_literals = []
        found_openers = {}
        arr_sizes = []

        try:
            t = tarfile.open(src_path, 'r:*')
        except Exception:
            # Fallback if we cannot open/parse the tarball
            return "AAAA<tag>BBBB", 4096

        with t:
            for member in t.getmembers():
                if not member.isfile():
                    continue
                name = member.name
                if not name.endswith(('.c', '.h', '.cpp', '.cxx', '.cc', '.hpp')):
                    continue
                f = t.extractfile(member)
                if f is None:
                    continue
                data_bytes = f.read()
                try:
                    text = data_bytes.decode('utf-8', errors='ignore')
                except Exception:
                    continue

                # Find literal tags like "<tag>"
                for m in re.finditer(r'"(<[^"\n]{1,64}>)"', text):
                    found_tag_literals.append(m.group(1))

                # Find char comparisons involving possible tag openers
                for m in re.finditer(r"[=!]=\s*'(.?)'", text):
                    ch = m.group(1)
                    if ch in openers_map:
                        found_openers[ch] = found_openers.get(ch, 0) + 1

                for m in re.finditer(r"case\s*'(.?)'\s*:", text):
                    ch = m.group(1)
                    if ch in openers_map:
                        found_openers[ch] = found_openers.get(ch, 0) + 1

                # Collect char array sizes
                for m in re.finditer(r'\bchar\s+[A-Za-z_]\w*\s*\[\s*(\d+)\s*\]', text):
                    try:
                        n = int(m.group(1))
                        if 8 <= n <= 65536:
                            arr_sizes.append(n)
                    except Exception:
                        pass

        # Decide on opener
        opener = '<'
        if found_openers:
            if '<' in found_openers:
                opener = '<'
            else:
                opener = max(found_openers.items(), key=lambda kv: kv[1])[0]
        closer = openers_map.get(opener, '>')

        # Build a base tag
        base_tag = None
        if found_tag_literals:
            # Prefer literals that match opener/closer
            for s in found_tag_literals:
                if len(s) >= 3 and s[0] == opener and s[-1] == closer:
                    base_tag = s
                    break
            if base_tag is None:
                base_tag = found_tag_literals[0]

            # Optionally concatenate several different tags to exercise more code
            unique_tags = []
            seen = set()
            total_len = 0
            for s in found_tag_literals:
                if s in seen:
                    continue
                seen.add(s)
                unique_tags.append(s)
                total_len += len(s)
                if total_len > 256 or len(unique_tags) >= 8:
                    break
            if unique_tags:
                base_tag = ''.join(unique_tags)
        if base_tag is None:
            if opener == '<' and closer == '>':
                base_tag = '<tag>'
            else:
                base_tag = opener + 'tag' + closer

        pattern = 'AAAA' + base_tag + 'BBBB'

        # Decide on target length based on discovered array sizes
        if arr_sizes:
            max_arr = max(arr_sizes)
            L_target = max(max_arr * 2, 2048)
            if L_target > 20000:
                L_target = 20000
        else:
            L_target = 4096

        return pattern, L_target

    def solve(self, src_path: str) -> bytes:
        pattern, target_len = self._analyze_source(src_path)

        if not pattern:
            pattern = "A"

        if target_len < len(pattern) + 1:
            target_len = len(pattern) * 2 + 1

        repetitions = target_len // len(pattern) + 2
        data_str = (pattern * repetitions)[: target_len - 1] + "\n"
        return data_str.encode('ascii', errors='replace')
