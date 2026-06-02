import os
import sys


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCHMARK_DIR = os.path.join(ROOT_DIR, "benchmarks")


benchmark_dict = {
    "ispd2005" : [f"adaptec{i}" for i in range(1, 4+1)] + [f"bigblue{i}" for i in range(1, 4+1)],
    "iccad2015" : [f"superblue{i}" for i in [1,3,4,5,7,10,16,18]],
}


benchmark_path_dict = {
    "ispd2005" : os.path.join(BENCHMARK_DIR, "ispd2005"),
    "iccad2015" : os.path.join(BENCHMARK_DIR, "iccad2015"),
}

benchmark_type_dict = {
    "ispd2005" : "aux",
    "iccad2015" : "def",
}


benchmark_power_config  = {
    "mp" : {
        "ispd2005" : 1e5,
        "iccad2015" : 1e5,
    },
    "gp" : {
        "ispd2005" : 1e7,
        "iccad2015" : 1e7,
    }
}

benchmark_n_macro_dict = {
    "ispd2005" : 1000000,
    "iccad2015" : 512
}