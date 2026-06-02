import os
import copy
import signal
import numpy as np
import torch as th
import socket
import json
import subprocess
import time
import select

from typing import overload

from utils.read_benchmark.read_aux import write_pl
from utils.read_benchmark.read_def import write_def
from utils.signal_handler import abort_signal_handler
from utils.debug import *
from utils.constant import INF

from thirdparty.dreamplace.Params import Params as DMPParams
from thirdparty.dreamplace.PlaceDB import PlaceDB as DMPPlaceDB
from thirdparty.dreamplace.NonLinearPlace import NonLinearPlace
import thirdparty.dreamplace.configure as configure
import thirdparty.dreamplace.ops.place_io.place_io as place_io

from PIL import Image


class GPEvaluator:
    DMP_CONFIG_PATH = "config/algorithm/dmp_config"
    DMP_TEMP_BENCHMARK_PATH = f"benchmarks/.tmp/GPEvaluator"
    SOCK_PATH = os.path.join(
        "sock_path",
        "dmp_worker_GPEvaluator_%(unique_token)s.sock"
    )
    AUX_FILES = [
        "%(benchmark)s.aux",
        "%(benchmark)s.scl",
        "%(benchmark)s.wts",
        "%(benchmark)s.nets",
        "%(benchmark)s.nodes"
    ]
    DEF_FILES = [
        "%(benchmark)s.lef",
        "%(benchmark)s.v",
        "%(benchmark)s.sdc",
        "%(benchmark)s_Early.lib",
        "%(benchmark)s_Late.lib"
    ]

    def __init__(self, args, placedb) -> None:
        self.args = args
        self.placedb = placedb

        self.dmp_params = DMPParams()
        self.dmp_placedb = None

    
        # load default dreamplace config
        self._load_dmp_config()
        os.environ["OMP_NUM_THREADS"] = str(self.dmp_params.num_threads)
        assert (not self.dmp_params.gpu) or configure.compile_configurations["CUDA_FOUND"] == 'TRUE', \
            "CANNOT enable GPU without CUDA compiled"

        # prepare benchmark
        self._prepare_benchmark()

        # prepare placement, figure database
        self.empty_saving_data()

        self.n_eval = 0

        self._worker = None
        self._sock = None
        self._sock_path = None
        self._worker_inited = False
        self.worker_path = os.path.join(self.args.SOURCE_DIR, "placer/dmp_worker.py")
        self.timeout_seconds = args.timeout_seconds
        self._sock_path = os.path.join(self.args.ROOT_DIR, GPEvaluator.SOCK_PATH % self.args.__dict__)
        os.makedirs(os.path.dirname(self._sock_path), exist_ok=True)

    def _cleanup_worker(self):
        if self._sock is not None:
            self._sock.close()
            self._sock = None
        if self._worker is not None:
            try:
                self._worker.terminate()
                try:
                    self._worker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self._worker.pid), signal.SIGKILL)
                    self._worker.wait()
            except Exception as e:
                pass
            finally:
                self._worker = None
        if self._sock_path is not None and os.path.exists(self._sock_path):
            os.unlink(self._sock_path)
        self._worker_inited = False

    def _ensure_worker(self):
        if self._worker is not None and \
           self._worker.poll() is None and \
           self._sock is not None:
            return True
        
        if os.path.exists(self._sock_path):
            os.unlink(self._sock_path)
        
        # init worker
        try:
            self._worker = subprocess.Popen(
                ["python3", self.worker_path, "--sock", self._sock_path],
                stdin=None,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=False,
                cwd=self.args.ROOT_DIR,
                preexec_fn=os.setsid  
            )
        except Exception:
            self._cleanup_worker()
            return False

        # init sock
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        deadline = time.time() + min(10, self.timeout_seconds)
        connected = False
        while time.time() < deadline:
            try:
                self._sock.connect(self._sock_path)
                connected = True
                break
            except Exception:
                time.sleep(0.05)
        if not connected:
            self._cleanup_worker()
            return False
        self._sock.settimeout(self.timeout_seconds)

        # init worker
        init_msg = json.dumps({
            "cmd": "init",
            "args": {
                "ROOT_DIR": self.args.ROOT_DIR,
                "temp_subdir": "GPEvaluator",
                "name": self.args.placer if not hasattr(self.args, "name") else self.args.name,
                "benchmark": self.args.benchmark,
                "benchmark_type": self.args.benchmark_type,
                "unique_token": self.args.unique_token,
                "seed": self.args.seed,
            },
            "canvas_width": self.placedb.canvas_width,
            "canvas_height": self.placedb.canvas_height,
        }) + "\n"
        try:
            self._sock.sendall(init_msg.encode())
            data = b""
            while True:
                chunk = self._sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:
                    break
            line = data.decode(errors="ignore").strip()
            ack_obj = json.loads(line) if line else {"ok": False}
        except:
            self._cleanup_worker()
            return False
        if not ack_obj.get("ok"):
            self._cleanup_worker()
            return False
        self._worker_inited = True
        return True

    def evaluate(self, macro_pos):
        if len(macro_pos) == 0:
            return INF

        if self.dmp_placedb is None:
            self._init_dmp(macro_pos=macro_pos)

        if not self._ensure_worker():
            return INF
        
        # eval request
        req = {
                "cmd": "eval_hpwl", 
                "macro_pos": macro_pos,
            }
        deadline = time.time() + self.timeout_seconds

        try:
            self._sock.sendall((json.dumps(req) + "\n").encode())
            remaining = deadline - time.time()
            if remaining <= 0:
                self._cleanup_worker()
                return INF
            r, _, _ = select.select([self._sock], [], [], remaining)
            if not r:
                self._cleanup_worker()
                return INF

            data = b""
            while True:
                remaining = deadline - time.time()
                if remaining <= 0:
                    self._cleanup_worker()
                    return INF

                chunk = self._sock.recv(65536)
                if not chunk:
                    break
                data += chunk
                if b"\n" in chunk:
                    break
            text = data.decode(errors="ignore")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            last_line = lines[-1] if lines else ""
            out = json.loads(last_line) if last_line else {"ok": False}
            if out.get("ok") and out.get("hpwl") is not None:
                hpwl = out["hpwl"]
                node_x = out.get("node_x")
                node_y = out.get("node_y")
                pos = out.get("pos")
                if node_x is not None and node_y is not None:
                    self.saving_data["placement"][hpwl] = (np.array(node_x, dtype=self.node_x_dtype),
                                                            np.array(node_y, dtype=self.node_y_dtype))
                if pos is not None:
                    self.saving_data["figure"][hpwl] = np.array(pos, dtype=self.pos_dtype)
                return hpwl
            return INF
        except KeyboardInterrupt:
            self._cleanup_worker()
            exit(0)
        except Exception:
            self._cleanup_worker()
            return INF

    
    def _init_dmp(self, macro_pos):
        self._prepare_placement_file(macro_pos=macro_pos)
        self.dmp_placedb = DMPPlaceDB()
        self.dmp_placedb(self.dmp_params)

        self.dmp_node_names = self.dmp_placedb.node_names.astype(np.str_)
        mask = np.char.find(self.dmp_node_names, "DREAMPlace") != -1
        modified_names = np.char.split(self.dmp_node_names[mask], '.').tolist()
        self.dmp_node_names[mask] = [name[0] for name in modified_names]
        self.placer = NonLinearPlace(self.dmp_params, self.dmp_placedb, timer=None)

        self.node_x_dtype = self.dmp_placedb.node_x.dtype
        self.node_y_dtype = self.dmp_placedb.node_y.dtype
        self.pos_dtype = self.placer.pos[0].data.clone().cpu().numpy().dtype
    
    
    def _load_dmp_config(self):
        ROOT_DIR = self.args.ROOT_DIR
        json_file = f"{self.args.benchmark}.json"
        json_path = os.path.join(
            ROOT_DIR,
            GPEvaluator.DMP_CONFIG_PATH,
            json_file
        )
        self.dmp_params.load(json_path)
        self.dmp_params.benchmark = self.args.benchmark
        self.dmp_params.random_center_init_flag = 1


    def _prepare_benchmark(self):
        os.makedirs(self._temp_benchmark_path, exist_ok=True)
        type_mapping = {
            "aux": self._prepare_benchmark_aux,
            "def": self._prepare_benchmark_def,
        }
        if self.args.benchmark_type in type_mapping:
            type_mapping[self.args.benchmark_type]()
        else:
            raise NotImplementedError
        
    def _prepare_benchmark_aux(self):
        self._link_files(GPEvaluator.AUX_FILES)

        suffix2path = \
            lambda suffix: os.path.join(
                self._temp_benchmark_path,
                "%(benchmark)s" % self.args.__dict__
            ) + suffix
        self.dmp_params.fromJson(
            {
                "aux_input": suffix2path(".aux")
            }
        )
        
    def _prepare_benchmark_def(self):
        self._link_files(GPEvaluator.DEF_FILES)

        suffix2path = \
            lambda suffix: os.path.join(
                self._temp_benchmark_path,
                "%(benchmark)s" % self.args.__dict__
            ) + suffix
        self.dmp_params.fromJson(
            {
                "def_input": suffix2path(".def"),
                "lef_input": suffix2path(".lef"),
                "verilog_input": suffix2path(".v"),
                "early_lib_input": suffix2path("_Early.lib"),
                "late_lib_input": suffix2path("_Late.lib"),
                "sdc_input": suffix2path(".sdc")
            }
        )

    def _link_files(self, files):
        for file_name in files:
            orig = os.path.join(
                self._orig_benchmark_path,
                file_name % self.args.__dict__)

            if not os.path.exists(orig):
                continue

            link = os.path.join(
                self._temp_benchmark_path,
                file_name % self.args.__dict__)
            
            os.system(f"ln -sfr {orig} {link}")

    def _prepare_placement_file(self, macro_pos):
        file_name = os.path.join(self._temp_benchmark_path, self.args.benchmark)
        type_mapping = {
            "aux" : lambda macro_pos, placedb : write_pl(file_name+".pl", macro_pos=macro_pos, placedb=placedb),
            "def" : lambda macro_pos, placedb : write_def(file_name+".def", macro_pos=macro_pos, placedb=placedb),
        }
        if self.args.benchmark_type in type_mapping:
            type_mapping[self.args.benchmark_type](macro_pos=macro_pos, placedb=self.placedb)
        else:
            raise NotImplementedError
        
    def empty_saving_data(self):
        self.saving_data = {
            "placement" : {},
            "figure" : {}
        }

    def _update_dmp_placedb(self, macro_pos):
        if self.args.benchmark_type == "aux":
            dmp_scale_factor_x, dmp_scale_factor_y = 1, 1
        else:
            dmp_scale_factor_x, dmp_scale_factor_y = self.dmp_placedb.xh/self.placedb.canvas_width, \
                                                     self.dmp_placedb.yh/self.placedb.canvas_height

        for macro in macro_pos:
            index = np.where(self.dmp_node_names == macro)
            pos_x = round(macro_pos[macro][0] * dmp_scale_factor_x) 
            pos_y = round(macro_pos[macro][1] * dmp_scale_factor_y) 
            self.dmp_placedb.node_x[index] = pos_x
            self.dmp_placedb.node_y[index] = pos_y
        
        node_x, node_y = self.dmp_placedb.unscale_pl(self.dmp_params.shift_factor, 
                                                     self.dmp_params.scale_factor)
        place_io.PlaceIOFunction.apply(self.dmp_placedb.rawdb, node_x, node_y, all_movable=True)
    
    def _update_dmp_placer(self):
        with th.no_grad():
            self.placer.pos[0].data.copy_(
                th.from_numpy(self.placer._initialize_position(self.dmp_params, self.dmp_placedb)).to(self.placer.device) )
            

    def save_placement(self, hpwl, placement_name):
        self.dmp_placedb.node_x[:] = self.saving_data["placement"][hpwl][0].copy()
        self.dmp_placedb.node_y[:] = self.saving_data["placement"][hpwl][1].copy()
        # unscale locations
        node_x, node_y = self.dmp_placedb.unscale_pl(self.dmp_params.shift_factor, 
                                                     self.dmp_params.scale_factor)
        # update raw database
        place_io.PlaceIOFunction.apply(self.dmp_placedb.rawdb, node_x, node_y, all_movable=True)

        self.dmp_placedb.write(
            self.dmp_params, 
            placement_name
        )
    
    def __deepcopy__(self, memo=None):
        return self
    
    def plot(self, hpwl:float, figure_name:str):
        pos = self.saving_data["figure"][hpwl]
        self.placer.plot(
            self.dmp_params,
            None,
            None,
            pos,
            figure_name, 
        )

        img = Image.open(figure_name)
        out = img.transpose(Image.FLIP_TOP_BOTTOM)
        img.close()
        out.save(figure_name)

    @property
    def _orig_benchmark_path(self):
        ROOT_DIR = self.args.ROOT_DIR
        return os.path.join(
            ROOT_DIR,
            self.args.benchmark_path
        )

    @property
    def _temp_benchmark_path(self):
        ROOT_DIR = self.args.ROOT_DIR
        return os.path.join(
            ROOT_DIR,
            GPEvaluator.DMP_TEMP_BENCHMARK_PATH,
            "%(benchmark)s_%(unique_token)s" % self.args.__dict__
        )



    
        
    

