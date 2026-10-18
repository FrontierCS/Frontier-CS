"""JSON whitespace must not change scores; malformed outputs are contestant errors."""
from pathlib import Path
import json,subprocess
import pytest
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def checker(tmp_path_factory):
    executable=tmp_path_factory.mktemp('checker1')/'checker'
    subprocess.run(['g++','-std=gnu++17','-O2','-I'+str(ROOT/'algorithmic/judge/include'),str(ROOT/'algorithmic/problems/1/chk.cc'),'-o',str(executable)],check=True)
    return executable

def run(checker,tmp_path,output,input_text=None):
    inf=tmp_path/'input';out=tmp_path/'output';ans=tmp_path/'answer'
    inf.write_text(input_text or json.dumps({chr(97+i):[10,10,1,1] for i in range(12)}))
    out.write_text(output);ans.write_text('0 120\n')
    return subprocess.run([str(checker),str(inf),str(out),str(ans)],capture_output=True,text=True,timeout=3)

@pytest.mark.parametrize('indent,separators',[(None,(',',':')),(None,(', ',': ')),(2,None)])
def test_valid_json_formats_get_identical_score(checker,tmp_path,indent,separators):
    output=json.dumps({chr(97+i):1 for i in range(12)},indent=indent,separators=separators)
    result=run(checker,tmp_path,output)
    assert result.returncode==7,result.stderr
    assert 'Ratio: 0.600000000000' in result.stderr

def test_ascii_unicode_escaped_key(checker,tmp_path):
    output=json.dumps({chr(97+i):1 for i in range(12)}).replace('"a"','"\\u0061"')
    assert run(checker,tmp_path,output).returncode==7

@pytest.mark.parametrize('output',['','{','{"unterminated', '{"a":1 "b":2}',
                                    '{"a":999999999999999999999999999}',
                                    '{"a":01}', '{"a":1.5}', '{"a":1,"a":2}'])
def test_invalid_json_is_not_judge_failure(checker,tmp_path,output):
    assert run(checker,tmp_path,output).returncode in (1,2)

def test_trailing_junk_rejected(checker,tmp_path):
    output=json.dumps({chr(97+i):1 for i in range(12)})+'garbage'
    assert run(checker,tmp_path,output).returncode in (1,2)

def test_invalid_judge_input_is_still_judge_failure(checker,tmp_path):
    assert run(checker,tmp_path,'{}',input_text='{').returncode==3
