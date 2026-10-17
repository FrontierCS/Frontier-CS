from pathlib import Path
import subprocess
import pytest
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module',params=['158','169'])
def checker(request,tmp_path_factory):
    pid=request.param;executable=tmp_path_factory.mktemp('checker'+pid)/'checker'
    subprocess.run(['g++','-std=gnu++17','-O2','-I'+str(ROOT/'algorithmic/judge/include'),str(ROOT/'algorithmic/problems'/pid/'chk.cc'),'-o',str(executable)],check=True)
    return pid,executable

def test_invalid_contestant_tokens_are_not_internal_errors(checker,tmp_path):
    pid,exe=checker;data=ROOT/'algorithmic/problems'/pid/'testdata'
    invalid=['','1\n0 0 0 0\n'] if pid=='158' else ['LL 0\n','? 0\n']
    for text in invalid:
        out=tmp_path/'output';out.write_text(text)
        result=subprocess.run([str(exe),str(data/'1.in'),str(out),str(data/'1.ans')],text=True,capture_output=True,timeout=3)
        assert result.returncode in (1,2),result.stderr
