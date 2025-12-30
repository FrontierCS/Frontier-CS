#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <tuple>
#include <set>
#include <chrono>
#include <random>
#include <bitset>
#include <unordered_map>
#include <cstring>

using namespace std;

const int N = 100;
const int L = 500000;

vector<long long> T(N);
vector<int> a(N), b(N);
vector<int> best_a(N), best_b(N);

mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

struct State {
    int current_employee;
    bitset<N> parities;

    bool operator==(const State& other) const {
        return current_employee == other.current_employee && parities == other.parities;
    }
};

struct StateHash {
    size_t operator()(const State& s) const {
        size_t h1 = hash<int>{}(s.current_employee);
        size_t h2 = 0;
        
        const size_t num_ull = (N + 63) / 64;
        unsigned long long temp_bitset[num_ull];
        memcpy(temp_bitset, &s.parities, sizeof(temp_bitset));
        
        for(size_t i = 0; i < num_ull; ++i) {
            h2 ^= hash<unsigned long long>{}(temp_bitset[i]) + 0x9e3779b9 + (h2 << 6) + (h2 >> 2);
        }

        return h1 ^ (h2 << 1);
    }
};


vector<long long> simulate(const vector<int>& current_a, const vector<int>& current_b) {
    vector<long long> counts(N, 0);
    bitset<N> parities;
    vector<int> path;
    path.reserve(L);

    unordered_map<State, int, StateHash> history;

    int current = 0;
    counts[0] = 1;
    parities.flip(0);
    path.push_back(0);

    for (int w = 1; w < L; ++w) {
        int prev = current;
        
        State s = {prev, parities};
        auto it = history.find(s);
        if (it != history.end()) {
            int w_prev = it->second;
            int cycle_len = w - w_prev;
            vector<int> cycle_counts(N, 0);
            for (int i = w_prev; i < w; ++i) {
                cycle_counts[path[i]]++;
            }

            int remaining_w = L - w;
            long long num_cycles = remaining_w / cycle_len;

            for (int i = 0; i < N; ++i) {
                counts[i] += num_cycles * cycle_counts[i];
            }

            int remaining_steps = remaining_w % cycle_len;
            for (int i = 0; i < remaining_steps; ++i) {
                counts[path[w_prev + i]]++;
            }
            return counts;
        }
        history[s] = w;
        
        if (parities[prev]) { // Odd count
            current = current_a[prev];
        } else { // Even count
            current = current_b[prev];
        }
        
        counts[current]++;
        parities.flip(current);
        path.push_back(current);
    }

    return counts;
}

long long calculate_error(const vector<long long>& counts) {
    long long error = 0;
    for (int i = 0; i < N; ++i) {
        error += abs(counts[i] - T[i]);
    }
    return error;
}

void solve_greedy() {
    vector<tuple<int, int, int>> items; // size, original_i, type (0 for a, 1 for b)
    for (int i = 0; i < N; ++i) {
        items.emplace_back((T[i] + 1) / 2, i, 0);
        items.emplace_back(T[i] / 2, i, 1);
    }
    sort(items.rbegin(), items.rend());

    vector<long long> needed = T;
    needed[0]--;

    set<pair<long long, int>, greater<pair<long long, int>>> pq;
    for (int i = 0; i < N; ++i) {
        pq.insert({needed[i], i});
    }

    for (const auto& [size, i, type] : items) {
        auto it = pq.begin();
        int target_j = it->second;
        pq.erase(it);

        if (type == 0) {
            a[i] = target_j;
        } else {
            b[i] = target_j;
        }
        
        needed[target_j] -= size;
        pq.insert({needed[target_j], target_j});
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    int n_dummy, l_dummy;
    cin >> n_dummy >> l_dummy;
    for (int i = 0; i < N; ++i) {
        cin >> T[i];
    }

    solve_greedy();
    
    best_a = a;
    best_b = b;
    
    auto counts = simulate(a, b);
    long long current_error = calculate_error(counts);
    long long best_error = current_error;

    double T_start = 1000.0;
    double T_end = 0.1;
    double time_limit = 1.95;

    uniform_int_distribution<int> dist_N(0, N - 1);
    uniform_int_distribution<int> dist_ab(0, 1);
    uniform_real_distribution<double> dist_01(0.0, 1.0);

    while(true) {
        auto current_time = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(current_time - start_time).count();
        if (elapsed > time_limit) {
            break;
        }
        
        double progress = elapsed / time_limit;
        double temp = T_start * pow(T_end / T_start, progress);

        int i = dist_N(rng);
        int j = dist_N(rng);
        int choice = dist_ab(rng);

        if (choice == 0) {
            int old_val = a[i];
            if (old_val == j) continue;
            a[i] = j;
            auto new_counts = simulate(a, b);
            long long new_error = calculate_error(new_counts);
            
            if (new_error < current_error || dist_01(rng) < exp((double)(current_error - new_error) / temp)) {
                current_error = new_error;
                if (current_error < best_error) {
                    best_error = current_error;
                    best_a = a;
                    best_b = b;
                }
            } else {
                a[i] = old_val;
            }
        } else {
            int old_val = b[i];
            if (old_val == j) continue;
            b[i] = j;
            auto new_counts = simulate(a, b);
            long long new_error = calculate_error(new_counts);

            if (new_error < current_error || dist_01(rng) < exp((double)(current_error - new_error) / temp)) {
                current_error = new_error;
                if (current_error < best_error) {
                    best_error = current_error;
                    best_a = a;
                    best_b = b;
                }
            } else {
                b[i] = old_val;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << best_a[i] << " " << best_b[i] << endl;
    }

    return 0;
}