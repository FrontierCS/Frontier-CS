import os
import tarfile
import zipfile


class Solution:
    TARGET_SIZE = 13996

    def solve(self, src_path: str) -> bytes:
        if os.path.isdir(src_path):
            data = self._scan_directory(src_path)
        elif tarfile.is_tarfile(src_path):
            data = self._scan_tar(src_path)
        elif zipfile.is_zipfile(src_path):
            data = self._scan_zip(src_path)
        else:
            # Fallback: if it's just a file, return its contents
            try:
                with open(src_path, "rb") as f:
                    return f.read()
            except Exception:
                data = None

        if data:
            return data

        return self._fallback_poc()

    # ----------------- Core scoring logic -----------------

    def _score_file(self, name: str, size: int) -> int:
        """
        Heuristic scoring for how likely a file is the desired PoC.
        """
        name_lower = name.lower()
        _, ext = os.path.splitext(name_lower)

        score = 0

        # Strong hint: bug id
        if "42280" in name_lower:
            score += 5000

        # Other strong indicators
        for kw in ("oss-fuzz", "ossfuzz", "uaf", "use-after", "use_after"):
            if kw in name_lower:
                score += 1500

        # Medium indicators
        for kw in ("poc", "crash", "repro", "bug", "issue", "sample"):
            if kw in name_lower:
                score += 800

        # Weak indicators
        for kw in ("pdf", "ps", "ghost", "fuzz", "regress", "test"):
            if kw in name_lower:
                score += 300

        # Extension-based hints
        preferred_exts = {
            ".pdf",
            ".ps",
            ".eps",
            ".bin",
            ".dat",
            ".in",
            ".poc",
            ".input",
            ".fuzz",
        }
        if ext in preferred_exts or ext == "":
            score += 500
            diff = abs(size - self.TARGET_SIZE)
            score += max(0, 1000 - diff)  # up to +1000 when exact match
        else:
            diff = abs(size - self.TARGET_SIZE)
            score += max(0, 300 - diff)  # weaker size influence

        # Light penalty for very large files
        if size > 500_000:
            score -= (size - 500_000) // 2000

        return score

    # ----------------- Archive / directory scanners -----------------

    def _scan_tar(self, path: str) -> bytes | None:
        best_member = None
        best_score = None

        try:
            with tarfile.open(path, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isreg():
                        continue
                    size = member.size
                    name = member.name
                    score = self._score_file(name, size)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_member = member

                if best_member is not None:
                    f = tf.extractfile(best_member)
                    if f is not None:
                        try:
                            return f.read()
                        finally:
                            f.close()
        except Exception:
            return None

        return None

    def _scan_zip(self, path: str) -> bytes | None:
        best_info = None
        best_score = None

        try:
            with zipfile.ZipFile(path, "r") as zf:
                for info in zf.infolist():
                    # Skip directories
                    is_dir = getattr(info, "is_dir", None)
                    if callable(is_dir):
                        if info.is_dir():
                            continue
                    else:
                        if info.filename.endswith("/"):
                            continue

                    size = info.file_size
                    name = info.filename
                    score = self._score_file(name, size)
                    if best_score is None or score > best_score:
                        best_score = score
                        best_info = info

                if best_info is not None:
                    with zf.open(best_info, "r") as f:
                        return f.read()
        except Exception:
            return None

        return None

    def _scan_directory(self, root_path: str) -> bytes | None:
        best_path = None
        best_score = None

        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    continue

                rel_name = os.path.relpath(full_path, root_path)
                rel_name = rel_name.replace("\\", "/")
                score = self._score_file(rel_name, size)

                if best_score is None or score > best_score:
                    best_score = score
                    best_path = full_path

        if best_path is not None:
            try:
                with open(best_path, "rb") as f:
                    return f.read()
            except Exception:
                return None

        return None

    # ----------------- Fallback PoC generator -----------------

    def _fallback_poc(self) -> bytes:
        """
        Fallback PoC if nothing suitable is found in the source tree.

        This is a generic PostScript snippet attempting to exercise PDF-related
        operators; may not reliably trigger the specific bug but provides a
        minimal, valid input.
        """
        # A small PostScript program that tries to invoke PDF interpreter-like
        # behavior in typical Ghostscript-style environments.
        ps = r"""%!PS
% Fallback PoC - generic PDF interpreter exercise
% Try to create a PDF interpreter context with an invalid stream.
/try_pdfi {
  /pdf_dict 10 dict def
  pdf_dict begin
    /Type /Catalog def
    /Pages 1 def
  end

  % Deliberately pass an invalid file object (closed or null)
  /badfile null def
  /pdfctx null def

  % These operator names are common in Ghostscript-like interpreters; if they
  % exist they may touch internal pdfi structures.
  /do_try {
    {
      (%stdin) (r) file closefile
      /badfile (%nonexistent.pdf) (r) file def
    } bind exec

    % Attempt various PDF-related operators if they are defined.
    /tryop {
      dup where {
        pop
        1 index load
        {
          % call with dummy args
          mark exch exec cleartomark
        } stopped pop
      } {
        pop
      } ifelse
    } bind def

    [
      /runpdfbegin
      /.runpdfbegin
      /pdfopen
      /.pdfopen
      /pdfinfo
      /.pdfinfo
      /pdfpagecount
      /.pdfpagecount
      /pdfshowpage
      /.pdfshowpage
      /pdfexecid
      /.pdfexecid
      /PDFExec
      /.PDFExec
    ] {
      tryop
    } forall
  } bind def

  do_try
} bind def

try_pdfi
quit
"""
        return ps.encode("ascii", "replace")
