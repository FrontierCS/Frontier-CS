INF = 1e16
EPS = 1e-8

def get_n_power(hpwl):
    n_power = 0
    while hpwl > 1:
        hpwl /= 10
        n_power += 1
    hpwl *= 10
    n_power -= 1
    return hpwl, n_power