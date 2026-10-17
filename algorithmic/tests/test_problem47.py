from pathlib import Path
import json,subprocess
import pytest
ROOT=Path(__file__).resolve().parents[2]

@pytest.fixture(scope='module')
def checker(tmp_path_factory):
    executable=tmp_path_factory.mktemp('checker47')/'checker'
    subprocess.run(['g++','-std=gnu++17','-O2','-I'+str(ROOT/'algorithmic/judge/include'),str(ROOT/'algorithmic/problems/47/chk.cc'),'-o',str(executable)],check=True)
    return executable

def run(checker,tmp_path,output):
    inf=tmp_path/'input';out=tmp_path/'output';ans=tmp_path/'answer'
    inf.write_text(json.dumps({'bin':{'W':10,'H':10,'allow_rotate':True},'items':[{'type':'A','w':2,'h':2,'v':5,'limit':10}]}))
    out.write_text(output);ans.write_text('0 10\n')
    return subprocess.run([str(checker),str(inf),str(out),str(ans)],capture_output=True,text=True,timeout=3)

@pytest.mark.parametrize('output',['','{','{"placements":[{"type":"unterminated',
                                    '{"placements":[{"type":"A","x":9223372036854775808}]}'])
def test_malformed_output_is_contestant_error(checker,tmp_path,output):
    assert run(checker,tmp_path,output).returncode in (1,2)

@pytest.mark.parametrize('x,y,rot',[(9223372036854775807,0,0),(0,9223372036854775807,0),(0,0,2),(0,0,-1)])
def test_overflowing_coordinates_and_invalid_rotation_rejected(checker,tmp_path,x,y,rot):
    output=json.dumps({'placements':[{'type':'A','x':x,'y':y,'rot':rot}]})
    assert run(checker,tmp_path,output).returncode==1

def test_boundary_placement_is_valid(checker,tmp_path):
    output=json.dumps({'placements':[{'type':'A','x':8,'y':8,'rot':1}]},separators=(',',':'))
    result=run(checker,tmp_path,output)
    assert result.returncode==7,result.stderr
    assert 'Ratio: 0.300000000000' in result.stderr
    assert run(checker,tmp_path,output+'extra').returncode in (1,2)

def test_unicode_escaped_type(checker,tmp_path):
    output='{"placements":[{"type":"\\u0041","x":0,"y":0,"rot":0}]}'
    assert run(checker,tmp_path,output).returncode==7
    assert run(checker,tmp_path,output.replace('\\u0041','\\q')).returncode==2
