import signal
from utils.debug import *

class AbortSignalException(Exception):
    pass

def abort_signal_handler(signum, frame):
    highlight("meet SIGABRT")
    raise AbortSignalException()

def timeout_handler(signum, frame):
    raise TimeoutError("Code execution timed out")

def cudaError_check(error_log_file):
    def get_last_line_not_empty(error_log_file):
        with open(error_log_file, 'r') as f:
            lines = f.readlines()
            for line in reversed(lines):
                stripped_line = line.strip()
                if stripped_line:
                    return stripped_line
        
        return None
    
    line = get_last_line_not_empty(error_log_file)
    if "CUDA" in line:
        return True
    else:
        return False