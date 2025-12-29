#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>
#include <random>
#include <chrono>

using namespace std;

const int N = 100;
const int L = 500000;

vector<int> T(N);

struct Solution {
    vector<int> a, b;
    long long error;
};

// Simulate the process and return the counts
vector<int> simulate(const vector<int>& current_a, const vector<int>& current_b) {
    vector<int> t(N, 0);
    int current_employee = 0;
    for (int week = 0; week < L; ++week) {
        int last_cleaner = current_employee;
        int count = t[last_cleaner];
        t[last_cleaner]++;
        if (count % 2 == 0) {
            current_employee = current_b[last_cleaner];
        } else {
            current_employee = current_a[last_cleaner];
        }
    }
    return t;
}

long long calculate_error(const vector<int>& t) {
    long long error = 0;
    for (int i = 0; i < N; ++i) {
        error += abs(t[i] - T[i]);
    }
    return error;
}

// Greedy initial solution
Solution get_initial_solution() {
    vector<int> res_a(N), res_b(N);

    // Heuristic based on bin packing
    vector<long long> demands(N);
    
    int min_T_idx = 0;
    for (int i = 1; i < N; ++i) {
        if (T[i] < T[min_T_idx]) {
            min_T_idx = i;
        }
    }

    vector<long long> O(N), E(N);
    for(int i=0; i<N; ++i){
        O[i] = T[i] / 2;
        E[i] = (T[i] + 1) / 2;
    }

    if (T[min_T_idx] > 0) {
        if (T[min_T_idx] % 2 != 0) { // T is odd, T-1 is even
            E[min_T_idx]--;
        } else { // T is even, T-1 is odd
            O[min_T_idx]--;
        }
    }
    
    for(int i=0; i<N; ++i){
        demands[i] = T[i];
    }
    if (demands[0] > 0) demands[0]--;

    struct Supply {
        long long val;
        int id;
        bool is_a; // true for a_i (odd), false for b_i (even)
        bool operator<(const Supply& other) const {
            return val > other.val;
        }
    };

    vector<Supply> supplies;
    for(int i=0; i<N; ++i){
        if (O[i] > 0) supplies.push_back({O[i], i, true});
        if (E[i] > 0) supplies.push_back({E[i], i, false});
    }
    sort(supplies.begin(), supplies.end());
    
    map<long long, vector<int>> demand_map;
    for(int i=0; i<N; ++i){
        if(demands[i] > 0) {
            demand_map[demands[i]].push_back(i);
        }
    }

    for(const auto& s : supplies){
        long long v = s.val;
        int id = s.id;
        bool is_a = s.is_a;

        auto it = demand_map.lower_bound(v);
        int target_j;

        if(it == demand_map.end()){
             if (demand_map.empty()) {
                target_j = id; // fallback
             } else {
                it = prev(demand_map.end());
                target_j = it->second.back();
             }
        } else {
            target_j = it->second.back();
        }
        
        long long old_demand = demands[target_j];
        demand_map[old_demand].pop_back();
        if(demand_map[old_demand].empty()){
            demand_map.erase(old_demand);
        }
        
        demands[target_j] -= v;
        if(demands[target_j] > 0) {
            demand_map[demands[target_j]].push_back(target_j);
        }

        if(is_a){
            res_a[id] = target_j;
        } else {
            res_b[id] = target_j;
        }
    }
    
    vector<int> t = simulate(res_a, res_b);
    return {res_a, res_b, calculate_error(t)};
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy, l_dummy;
    cin >> n_dummy >> l_dummy;
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }

    auto start_time = chrono::high_resolution_clock::now();

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    Solution best_sol = get_initial_solution();
    Solution current_sol = best_sol;
    
    double time_limit = 1.9; 

    double start_temp = 2000;
    double end_temp = 1;

    while(true){
        auto current_time = chrono::high_resolution_clock::now();
        double elapsed_time = chrono::duration_cast<chrono::duration<double>>(current_time - start_time).count();
        if (elapsed_time > time_limit) {
            break;
        }

        int change_idx = rng() % (2 * N);
        int new_val = rng() % N;

        Solution next_sol = current_sol;
        
        if (change_idx < N) {
            if (next_sol.a[change_idx] == new_val) continue;
            next_sol.a[change_idx] = new_val;
        } else {
            change_idx -= N;
            if (next_sol.b[change_idx] == new_val) continue;
            next_sol.b[change_idx] = new_val;
        }

        vector<int> t = simulate(next_sol.a, next_sol.b);
        next_sol.error = calculate_error(t);
        
        double temp = start_temp + (end_temp - start_temp) * (elapsed_time / time_limit);
        
        if (next_sol.error < current_sol.error) {
            current_sol = next_sol;
            if(current_sol.error < best_sol.error){
                best_sol = current_sol;
            }
        } else {
            double acceptance_prob = exp((double)(current_sol.error - next_sol.error) / temp);
            if ((double)rng() / rng.max() < acceptance_prob) {
                current_sol = next_sol;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << best_sol.a[i] << " " << best_sol.b[i] << endl;
    }

    return 0;
}