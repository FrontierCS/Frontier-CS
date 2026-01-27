#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <ctime>
#include <cmath>
#include <random>

using namespace std;

// Fast random number generator
struct Xorshift {
    unsigned int x = 123456789;
    unsigned int y = 362436069;
    unsigned int z = 521288629;
    unsigned int w = 88675123;
    unsigned int next() {
        unsigned int t = x ^ (x << 11);
        x = y; y = z; z = w;
        return w = w ^ (w >> 19) ^ t ^ (t >> 8);
    }
    int next(int max_val) {
        if (max_val < 0) return 0;
        return next() % (max_val + 1);
    }
    double nextDouble() {
        return (double)next() / 4294967295.0;
    }
} rng;

int n;
vector<int> D; 
vector<int> F_flat;
vector<vector<int>> outF, inF;
vector<int> p;

long long calculate_total_cost() {
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        for (int k : outF[i]) {
            cost += D[p[i] * n + p[k]];
        }
    }
    return cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    D.resize(n * n);
    vector<int> degD(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> D[i * n + j];
            // Degree is sum of edges connected to a node (in + out)
            if (D[i * n + j]) {
                degD[i]++;
                degD[j]++;
            }
        }
    }

    F_flat.resize(n * n);
    outF.resize(n);
    inF.resize(n);
    vector<int> degF(n, 0);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val;
            cin >> val;
            F_flat[i * n + j] = val;
            if (val) {
                outF[i].push_back(j);
                inF[j].push_back(i);
                degF[i]++;
                degF[j]++;
            }
        }
    }

    // Heuristic initialization:
    // Sort facilities by F-degree (descending)
    // Sort locations by D-degree (ascending)
    // Rationale: High flow nodes should go to locations with low distance/connectivity 
    // to minimize the chance of hitting a 1 in D (since we want D=0 when F=1).
    p.resize(n);
    vector<int> facilities(n);
    iota(facilities.begin(), facilities.end(), 0);
    vector<int> locations(n);
    iota(locations.begin(), locations.end(), 0);

    sort(facilities.begin(), facilities.end(), [&](int a, int b) {
        return degF[a] > degF[b];
    });
    sort(locations.begin(), locations.end(), [&](int a, int b) {
        return degD[a] < degD[b];
    });

    for (int i = 0; i < n; ++i) {
        p[facilities[i]] = locations[i];
    }

    long long current_cost = calculate_total_cost();
    long long best_cost = current_cost;
    vector<int> best_p = p;

    // Simulated Annealing
    double start_time = (double)clock() / CLOCKS_PER_SEC;
    // Set time limit slightly less than typical 2.0s to be safe
    double time_limit = 1.95; 
    
    // Initial temp and cooling
    // Since we start from a good heuristic, we don't want T to be too high to scramble it completely,
    // but high enough to escape local optima.
    // Normalized cost differences are typically integers. 
    double t_start = 2.5; 
    double t_end = 0.01;
    double temp = t_start;
    
    int iter = 0;
    
    while (true) {
        // Check time every 256 iterations to reduce overhead
        if ((iter & 255) == 0) {
            double curr_time = (double)clock() / CLOCKS_PER_SEC;
            if (curr_time > time_limit) break;
            
            // Update temperature
            double progress = (curr_time - start_time) / (time_limit - start_time);
            // Exponential cooling
            temp = t_start * pow(t_end / t_start, progress);
        }
        
        // Pick u, v
        int u = rng.next(n - 1);
        int v = rng.next(n - 1);
        if (u == v) {
            v = (u + 1) % n;
        }

        int lu = p[u];
        int lv = p[v];

        long long delta = 0;

        // Calculate delta efficiently by iterating only neighbors in F
        // u moves lu -> lv, v moves lv -> lu

        // Edges from u
        for (int k : outF[u]) {
            if (k == u || k == v) continue;
            // Old term: F_uk * D[lu, p[k]]
            // New term: F_uk * D[lv, p[k]]
            delta += (D[lv * n + p[k]] - D[lu * n + p[k]]);
        }
        // Edges to u
        for (int k : inF[u]) {
            if (k == u || k == v) continue;
            delta += (D[p[k] * n + lv] - D[p[k] * n + lu]);
        }
        
        // Edges from v
        for (int k : outF[v]) {
            if (k == u || k == v) continue;
            delta += (D[lu * n + p[k]] - D[lv * n + p[k]]);
        }
        // Edges to v
        for (int k : inF[v]) {
            if (k == u || k == v) continue;
            delta += (D[p[k] * n + lu] - D[p[k] * n + lv]);
        }

        // Interaction u-v
        if (F_flat[u * n + v]) {
            // Old: D[lu, lv], New: D[lv, lu]
            delta += (D[lv * n + lu] - D[lu * n + lv]);
        }
        if (F_flat[v * n + u]) {
            // Old: D[lv, lu], New: D[lu, lv]
            delta += (D[lu * n + lv] - D[lv * n + lu]);
        }

        // Self loops
        if (F_flat[u * n + u]) {
            delta += (D[lv * n + lv] - D[lu * n + lu]);
        }
        if (F_flat[v * n + v]) {
            delta += (D[lu * n + lu] - D[lv * n + lv]);
        }

        bool accept = false;
        if (delta < 0) {
            accept = true;
        } else if (temp > 1e-9) {
             // Optimization: if delta is too large, exp is 0
             if (delta < temp * 10.0) { 
                 if (rng.nextDouble() < exp(-delta / temp)) {
                     accept = true;
                 }
             }
        }

        if (accept) {
            swap(p[u], p[v]);
            current_cost += delta;
            if (current_cost < best_cost) {
                best_cost = current_cost;
                best_p = p;
            }
        }
        
        iter++;
    }

    for (int i = 0; i < n; ++i) {
        cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}