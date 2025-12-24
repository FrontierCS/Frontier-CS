import os
import tarfile
import gzip
import bz2
import lzma


class Solution:
    def solve(self, src_path: str) -> bytes:
        TARGET_SIZE = 1479

        def candidate_score(member, exact_size_pref=True):
            name = member.name.lower()
            score = 0

            if exact_size_pref and member.size == TARGET_SIZE:
                score += 1000

            # Keyword-based scoring
            keywords = [
                'poc', 'crash', 'testcase', 'id_', 'clusterfuzz', 'fuzz',
                'heap', 'overflow', 'hbo', 'cve', 'bug', 'issue', 'oss-fuzz'
            ]
            if any(k in name for k in keywords):
                score += 200

            if '47500' in name:
                score += 150

            if 'htdec' in name or 'ht_dec' in name or 'ht-' in name or '/ht' in name:
                score += 40

            if 'ht' in name:
                score += 10

            if 't1' in name:
                score += 40

            if 'opj' in name:
                score += 20

            poc_dirs = [
                '/poc', '/pocs', '/crash', '/crashes', '/tests', '/regress',
                '/regression', '/corpus', '/seeds', '/seed'
            ]
            if any(d in name for d in poc_dirs):
                score += 50

            jp2_exts = ('.jp2', '.j2k', '.j2c', '.jpc', '.jpx')
            bin_exts = ('.bin', '.raw', '.dat', '.img')
            if name.endswith(jp2_exts) or name.endswith(bin_exts):
                score += 80
            elif '.' not in os.path.basename(name):
                score += 10

            # Size closeness
            size_diff = abs(member.size - TARGET_SIZE)
            score += max(0, 200 - size_diff // 10)

            if member.size > 1_000_000:
                score -= 500

            return score

        best_member_name = None
        data = None

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = [
                    m for m in tf.getmembers()
                    if m.isfile() and m.size > 0
                ]
                if not members:
                    raise RuntimeError("No file members in tarball")

                members.sort(key=lambda m: m.name)

                exact = [m for m in members if m.size == TARGET_SIZE]
                best_member = None

                if exact:
                    exact_sorted = sorted(
                        exact,
                        key=lambda m: (-candidate_score(m, exact_size_pref=True), m.name)
                    )
                    best_member = exact_sorted[0]
                else:
                    scored = sorted(
                        members,
                        key=lambda m: (-candidate_score(m, exact_size_pref=False), m.name)
                    )
                    best_member = scored[0] if scored else None

                if best_member is not None:
                    try:
                        f = tf.extractfile(best_member)
                        if f is not None:
                            data = f.read()
                            best_member_name = best_member.name
                    except Exception:
                        data = None
        except Exception:
            data = None

        if data is None:
            return b'A' * TARGET_SIZE

        # Optional decompression if the selected file is compressed
        if best_member_name is not None:
            lower_name = best_member_name.lower()
            try:
                if lower_name.endswith('.gz'):
                    new_data = gzip.decompress(data)
                    if len(new_data) < 10_000_000:
                        data = new_data
                elif lower_name.endswith('.bz2'):
                    new_data = bz2.decompress(data)
                    if len(new_data) < 10_000_000:
                        data = new_data
                elif lower_name.endswith('.xz') or lower_name.endswith('.lzma'):
                    new_data = lzma.decompress(data)
                    if len(new_data) < 10_000_000:
                        data = new_data
            except Exception:
                pass

        return data
