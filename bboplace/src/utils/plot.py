import os 
import sys
import argparse
import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THIRDPARTY_DIR = os.path.join(ROOT_DIR, "thirdparty")
SOURCE_DIR = os.path.join(ROOT_DIR, "src")
sys.path.append(ROOT_DIR)
sys.path.append(THIRDPARTY_DIR)
sys.path.append(SOURCE_DIR)
os.environ["PYTHONPATH"] = ":".join(sys.path)

from thirdparty.dreamplace.Params import Params as DMPParams
from thirdparty.dreamplace.PlaceDB import PlaceDB as DMPPlaceDB
from thirdparty.dreamplace.NonLinearPlace import NonLinearPlace
from PIL import Image

from utils.debug import *

parser = argparse.ArgumentParser(description='plot parser')
parser.add_argument("--placement_path", required=True, type=str)
parser.add_argument("--benchmark", required=True, type=str)
parser.add_argument("--dataset", required=True, type=str, help="choose from ['ispd2005', 'iccad2015']")
args = parser.parse_args()
# set unique token
unique_token = "{}".format(datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
args.unique_token = unique_token


class Plot:
    DMP_CONFIG_PATH = "config/algorithm/dmp_config"
    DMP_BENCHMARK_PATH = "benchmarks"
    DMP_TEMP_BENCHMARK_PATH = os.path.join(DMP_BENCHMARK_PATH, ".tmp/Plot")

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

    def __init__(self, args) -> None:
        self.args = args

        self.file_name, self.file_format = os.path.splitext(os.path.basename(args.placement_path))
        self.file_format = self.file_format[1:]
        self.placement_path_dir = os.path.dirname(args.placement_path)
        
        self.dmp_params = DMPParams()
        self.dmp_placedb = DMPPlaceDB()

        # prepare benchmark
        self._prepare_benchmark()

        self.dmp_placedb(self.dmp_params)
        self.dmp_placer = NonLinearPlace(
            params=self.dmp_params,
            placedb=self.dmp_placedb,
            timer=None
        )

    def plot(self):
        pos = self.dmp_placer.pos[0].data.clone().cpu().numpy()
        figure_name = os.path.join(self.placement_path_dir, self.file_name + ".png")
        self.dmp_placer.plot(
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

    def _prepare_benchmark(self):
        os.makedirs(self._temp_benchmark_path, exist_ok=True)
        link_placement = os.path.join(self._temp_benchmark_path, f"{self.args.benchmark}.{self.file_format}")
        os.system(f"ln -sfr {self.args.placement_path} {link_placement}")
        
        type_mapping = {
            "pl": self._prepare_benchmark_aux,
            "def": self._prepare_benchmark_def,
        }
        if self.file_format in type_mapping:
            type_mapping[self.file_format]()
        else:
            raise NotImplementedError
        
        self.dmp_params.random_center_init_flag = 0

    def _prepare_benchmark_aux(self):
        self._link_files(Plot.AUX_FILES)

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
        self._link_files(Plot.DEF_FILES)

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
                file_name % self.args.__dict__
            )
            
            os.system(f"ln -sfr {orig} {link}")
    
    @property
    def _orig_benchmark_path(self):
        return os.path.join(
            ROOT_DIR,
            Plot.DMP_BENCHMARK_PATH,
            self.args.dataset,
            self.args.benchmark
        )

    @property
    def _temp_benchmark_path(self):
        return os.path.join(
            ROOT_DIR,
            Plot.DMP_TEMP_BENCHMARK_PATH,
            "%(benchmark)s_%(unique_token)s" % self.args.__dict__
        )
    
    def cleanup(self):
        if os.path.exists(self._temp_benchmark_path):
            os.system(f"rm -r {self._temp_benchmark_path}")

if __name__ == "__main__":
    plot = Plot(args=args)
    try:
        plot.plot()
    finally:
        plot.cleanup()