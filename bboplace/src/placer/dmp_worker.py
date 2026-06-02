import json
import sys
import os
import torch as th
import socket
import numpy as np
import signal
import time
import threading
import psutil
import thirdparty.dreamplace.ops.place_io.place_io as place_io

from thirdparty.dreamplace.Params import Params as DMPParams
from thirdparty.dreamplace.PlaceDB import PlaceDB as DMPPlaceDB
from thirdparty.dreamplace.NonLinearPlace import NonLinearPlace

from src.utils.debug import *


def _setup_inputs(params: DMPParams, args: dict):
    json_path = os.path.join(
        args["ROOT_DIR"],
        "config/algorithm/dmp_config",
        f"{args['benchmark']}.json",
    )
    params.load(json_path)

    temp_subdir = args.get("temp_subdir", "HPO")
    temp_benchmark_path = os.path.join(
        args["ROOT_DIR"],
        f"benchmarks/.tmp/{temp_subdir}",
        f"{args['benchmark']}_{args['unique_token']}",
    )

    def suffix2path(suffix: str) -> str:
        return os.path.join(temp_benchmark_path, f"{args['benchmark']}") + suffix

    if args["benchmark_type"] == "aux":
        params.fromJson({
            "aux_input": suffix2path(".aux")
        })
    elif args["benchmark_type"] == "def":
        params.fromJson({
            "def_input": suffix2path(".def"),
            "lef_input": suffix2path(".lef"),
            "verilog_input": suffix2path(".v"),
            "early_lib_input": suffix2path("_Early.lib"),
            "late_lib_input": suffix2path("_Late.lib"),
            "sdc_input": suffix2path(".sdc"),
        })
    else:
        raise RuntimeError("Unsupported benchmark_type")

    params.fromJson({
        "plot_flag": 0,
        "timing_opt_flag": 0,
        "random_seed": args["seed"],
        "result_dir": os.path.join(
            args["ROOT_DIR"],
            "results",
            f"{args['name']}",
            f"{args['benchmark']}",
            f"{args['unique_token']}",
            "dmp_results",
        ),
        "random_center_init_flag": 1,
    })


class DMPWorker:
    def __init__(self):
        self.init = False
        self.args = None
        self.canvas_width = None
        self.canvas_height = None

        self.params = DMPParams()
        self.placedb = DMPPlaceDB()
        self.placer = None

        self.node_names = None
        self.server = None
        self.sock_path = None
        
        self._parent_pid = os.getppid()  
        self._monitor_thread = None
    
    def _init_data(self, args: dict, canvas_width: float, canvas_height: float):
        self.args = args
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        _setup_inputs(self.params, self.args)

        self.placedb(self.params)
        self.placer = NonLinearPlace(self.params, self.placedb, timer=None)

        # cache node_names for evaluator
        self.node_names = self.placedb.node_names.astype('U')
        mask = np.char.find(self.node_names, "DREAMPlace") != -1
        modified = np.char.split(self.node_names[mask], '.').tolist()
        self.node_names[mask] = [n[0] for n in modified]

        self.init = True

    def _start_parent_monitor(self):
        def cleanup_worker():
            if self.server:
                self.server.close()
            if self.sock_path is not None and os.path.exists(self.sock_path):
                os.unlink(self.sock_path)
            os._exit(0)
        
        def monitor_parent():
            while True:
                try:
                    if not psutil.pid_exists(self._parent_pid):
                        cleanup_worker()
                    
                    try:
                        parent = psutil.Process(self._parent_pid)
                        if parent.create_time() != psutil.Process(os.getppid()).create_time():
                            cleanup_worker()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        cleanup_worker()
                        
                except Exception as e:
                    cleanup_worker()
                    
                time.sleep(1)  
        
        self._monitor_thread = threading.Thread(target=monitor_parent, daemon=True)
        self._monitor_thread.start()

    def handle_place(self, msg: dict) -> dict:
        params_update = msg.get("params_update")

        if isinstance(params_update, dict):
            self.params.fromJson(params_update)
        with th.no_grad():
            self.placer.pos[0].data.copy_(
                th.from_numpy(self.placer._initialize_position(self.params, self.placedb)).to(self.placer.device)
            )
        _ = self.placer(self.params, self.placedb)
        macro_pos = self.placedb.export(self.params, msg["macro_lst"])
        for node_name in list(macro_pos.keys()):
            x = macro_pos[node_name][0] / (self.placedb.xh - self.placedb.xl) * self.canvas_width
            y = macro_pos[node_name][1] / (self.placedb.yh - self.placedb.yl) * self.canvas_height
            macro_pos[node_name] = [x, y]
        return {"ok": True, "macro_pos": macro_pos}

    def handle_eval_hpwl(self, msg: dict) -> dict:
        macro_pos = msg["macro_pos"]
        if self.args["benchmark_type"] == "aux":
            dmp_scale_factor_x, dmp_scale_factor_y = 1, 1
        else:
            dmp_scale_factor_x = self.placedb.xh / self.canvas_width
            dmp_scale_factor_y = self.placedb.yh / self.canvas_height
        
        for macro, pos in macro_pos.items():
            index = np.where(self.node_names == macro)
            pos_x = round(pos[0] * dmp_scale_factor_x)
            pos_y = round(pos[1] * dmp_scale_factor_y)
            self.placedb.node_x[index] = pos_x
            self.placedb.node_y[index] = pos_y
        node_x, node_y = self.placedb.unscale_pl(self.params.shift_factor, self.params.scale_factor)
        place_io.PlaceIOFunction.apply(self.placedb.rawdb, node_x, node_y, all_movable=True)

        with th.no_grad():
            self.placer.pos[0].data.copy_(
                th.from_numpy(self.placer._initialize_position(self.params, self.placedb)).to(self.placer.device)
            )
        metrics = self.placer(self.params, self.placedb)
        try:
            hpwl = metrics[-1].hpwl.cpu().item()
        except Exception:
            hpwl = None
        try:
            pos_arr = self.placer.pos[0].data.detach().cpu().numpy().tolist()
        except Exception:
            pos_arr = None
        try:
            node_x_list = self.placedb.node_x.tolist()
            node_y_list = self.placedb.node_y.tolist()
        except Exception:
            node_x_list, node_y_list = None, None
        return {
            "ok": True,
            "hpwl": hpwl,
            "pos": pos_arr,
            "node_x": node_x_list,
            "node_y": node_y_list,
        }

    def serve_forever(self, sock_path: str):
        if os.path.exists(sock_path):
            os.unlink(sock_path)
        self.sock_path = sock_path
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(sock_path)
        self.server.listen(1)

        self._start_parent_monitor()
        while True:
            try:
                conn, _ = self.server.accept()
            except Exception:
                continue
            with conn:
                buffer = b""
                while True:
                    try:
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        buffer += chunk
                        while b"\n" in buffer:
                            line_bytes, buffer = buffer.split(b"\n", 1)
                            line = line_bytes.decode(errors="ignore").strip()
                            if not line:
                                continue
                            try:
                                msg = json.loads(line)
                            except Exception as e:
                                try:
                                    conn.sendall((json.dumps({"ok": False, "error": str(e)}) + "\n").encode())
                                except Exception:
                                    pass
                                continue

                            try:
                                cmd = msg.get("cmd")
                                if cmd == "init":
                                    try:
                                        if not self.init:
                                            args = msg.get("args")
                                            canvas_width = msg.get("canvas_width")
                                            canvas_height = msg.get("canvas_height")
                                            
                                            self._init_data(args, canvas_width, canvas_height)
                                            conn.sendall((json.dumps({"ok": True, "action": "init"}) + "\n").encode())
                                    except Exception as e:
                                        try:
                                            conn.sendall((json.dumps({"ok": False, "error": "init failed: " + str(e)}) + "\n").encode())
                                        except Exception:
                                            pass
                                        continue
                                elif cmd == "place":
                                    resp = self.handle_place(msg)
                                elif cmd == "eval_hpwl":
                                    resp = self.handle_eval_hpwl(msg)
                                elif cmd == "ping":
                                    resp = {"ok": True, "status": "alive"}
                                else:
                                    resp = {"ok": False, "error": "unknown cmd"}
                            except Exception as e:
                                resp = {"ok": False, "error": str(e)}
                            try:
                                conn.sendall((json.dumps(resp) + "\n").encode())
                            except Exception:
                                break
                    except Exception:
                        break


def run_once(input_json_path):
    with open(input_json_path, "r") as f:
        cfg = json.load(f)

    args = cfg["args"]
    macro_lst = cfg["macro_lst"]
    canvas_width = cfg["canvas_width"]
    canvas_height = cfg["canvas_height"]

    params = DMPParams()
    placedb = DMPPlaceDB()
    _setup_inputs(params, args)

    placedb(params)
    placer = NonLinearPlace(params, placedb, timer=None)

    with th.no_grad():
        placer.pos[0].data.copy_(
            th.from_numpy(placer._initialize_position(params, placedb)).to(placer.device)
        )

    _ = placer(params, placedb)

    macro_pos = placedb.export(params, macro_lst)
    for node_name in list(macro_pos.keys()):
        x = macro_pos[node_name][0] / (placedb.xh - placedb.xl) * canvas_width
        y = macro_pos[node_name][1] / (placedb.yh - placedb.yl) * canvas_height
        macro_pos[node_name] = [x, y]

    print(json.dumps({"ok": True, "macro_pos": macro_pos}))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] not in ("--loop", "--sock"):
        try:
            run_once(sys.argv[1])
        except Exception as e:
            print(json.dumps({"ok": False, "error": str(e)}))
            sys.exit(2)
        sys.exit(0)

    if len(sys.argv) == 3 and sys.argv[1] == "--sock":
        sock_path = sys.argv[2]
        worker = DMPWorker()
        print("\nbefore into serve_forever\n", flush=True)
        worker.serve_forever(sock_path)
        