#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <tuple>

using namespace std;

const int N = 100;
const int L = 500000;

struct Solution {
    vector<int> a, b;
};

vector<long long> T_target;
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
auto start_time = chrono::high_resolution_clock::now();

void simulate(const Solution& sol, vector<int>& t, int num_weeks) {
    t.assign(N, 0);
    int current_cleaner = 0;
    for (int week = 0; week < num_weeks; ++week) {
        t[current_cleaner]++;
        int count = t[current_cleaner];
        int last_cleaner = current_cleaner;
        if (week < num_weeks - 1) {
            if (count % 2 != 0) {
                current_cleaner = sol.a[last_cleaner];
            } else {
                current_cleaner = sol.b[last_cleaner];
            }
        }
    }
}

long long calculate_proxy_error(const vector<int>& t, int short_L) {
    long long error = 0;
    double scale = (double)L / short_L;
    for (int i = 0; i < N; ++i) {
        error += abs((long long)round(t[i] * scale) - T_target[i]);
    }
    return error;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy, l_dummy;
    cin >> n_dummy >> l_dummy;

    T_target.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> T_target[i];
    }

    Solution current_sol;
    current_sol.a.resize(N);
    current_sol.b.resize(N);
    for (int i = 0; i < N; ++i) {
        current_sol.a[i] = uniform_int_distribution<int>(0, N - 1)(rng);
        current_sol.b[i] = uniform_int_distribution<int>(0, N - 1)(rng);
    }
    
    int short_L = N * N * 2;
    if (short_L > L) short_L = L;

    vector<int> t_counts;
    simulate(current_sol, t_counts, short_L);
    long long current_error_proxy = calculate_proxy_error(t_counts, short_L);

    Solution best_sol = current_sol;
    long long best_error_proxy = current_error_proxy;
    
    double start_temp = 10000;
    double end_temp = 10;
    double time_limit_ms = 1950.0;

    while (true) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed_ms = chrono::duration_cast<chrono::microseconds>(now - start_time).count() / 1000.0;
        if (elapsed_ms > time_limit_ms) break;

        double temp = start_temp + (end_temp - start_temp) * elapsed_ms / time_limit_ms;

        int i = uniform_int_distribution<int>(0, N - 1)(rng);
        int type = uniform_int_distribution<int>(0, 1)(rng);
        int new_val = uniform_int_distribution<int>(0, N - 1)(rng);

        Solution next_sol = current_sol;
        long long old_val;
        if (type == 0) {
            old_val = next_sol.a[i];
            if (old_val == new_val) continue;
            next_sol.a[i] = new_val;
        } else {
            old_val = next_sol.b[i];
            if (old_val == new_val) continue;
            next_sol.b[i] = new_val;
        }
        
        vector<int> next_t_counts;
        simulate(next_sol, next_t_counts, short_L);
        long long next_error_proxy = calculate_proxy_error(next_t_counts, short_L);
        
        long long delta_error = next_error_proxy - current_error_proxy;

        if (delta_error < 0 || uniform_real_distribution<double>(0.0, 1.0)(rng) < exp(-delta_error / temp)) {
            current_sol = next_sol;
            current_error_proxy = next_error_proxy;
            if (current_error_proxy < best_error_proxy) {
                best_error_proxy = current_error_proxy;
                best_sol = current_sol;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << best_sol.a[i] << " " << best_sol.b[i] << "\n";
    }

    return 0;
}