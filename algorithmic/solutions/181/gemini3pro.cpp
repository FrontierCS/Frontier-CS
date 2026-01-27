#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Global data structures
int n;
// D is distance matrix. Using int8_t to save memory, values are 0 or 1.
int8_t D[2005][2005];
// F_mat for O(1) checking of flow existence
int8_t F_mat[2005][2005];
// Adjacency lists for F to speed up delta calculation
vector<int> F_out[2005];
vector<int> F_in[2005];

// Current permutation: p[facility] = location
int p[2005];

// Calculate full cost from scratch
long long calculate_total_cost() {
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (F_mat[i][j] && D[p[i]][p[j]]) {
                cost++;
            }
        }
    }
    return cost;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Read Distance Matrix D
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val;
            cin >> val;
            D[i][j] = (int8_t)val;
        }
    }

    // Read Flow Matrix F
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val;
            cin >> val;
            F_mat[i][j] = (int8_t)val;
            if (val) {
                F_out[i].push_back(j);
                F_in[j].push_back(i);
            }
        }
    }

    // Heuristic Initialization based on degrees
    // We want to map high-degree nodes in F (dense flow) to low-degree nodes in D (sparse distance)
    // to minimize the collision of (F=1, D=1).
    vector<pair<int, int>> degF(n), degD(n);

    for (int i = 0; i < n; ++i) {
        int d = 0;
        // Check out-neighbors
        for (int neighbor : F_out[i]) d++;
        // Check in-neighbors
        for (int neighbor : F_in[i]) d++;
        degF[i] = {d, i};
    }

    for (int i = 0; i < n; ++i) {
        int d = 0;
        for (int j = 0; j < n; ++j) {
            if (D[i][j]) d++;
            if (D[j][i]) d++;
        }
        degD[i] = {d, i};
    }

    // Sort F degrees descending (high flow first)
    sort(degF.rbegin(), degF.rend());
    // Sort D degrees ascending (low distance first)
    sort(degD.begin(), degD.end());

    // Assign facilities to locations
    // The i-th "most connected" facility goes to the i-th "least connected" location
    for (int k = 0; k < n; ++k) {
        p[degF[k].second] = degD[k].second;
    }

    long long current_cost = calculate_total_cost();

    // Simulated Annealing setup
    mt19937 rng(1337);
    uniform_int_distribution<int> dist_n(0, n - 1);
    uniform_real_distribution<double> dist_real(0.0, 1.0);

    auto start_time = chrono::steady_clock::now();
    // Time limit slightly less than typical 2.0s to be safe
    double time_limit = 1.90; 
    
    // Initial temperature and cooling schedule
    double T_start = 0.5;
    double T_end = 1e-4;
    double T = T_start;

    int iter_batch = 2048; // Check time every 2048 iterations
    int counter = 0;

    while (true) {
        // Periodic time check and temperature update
        if ((counter & (iter_batch - 1)) == 0) {
            auto now = chrono::steady_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            double t_elapsed = elapsed.count();
            if (t_elapsed > time_limit) break;
            
            // Exponential cooling
            double progress = t_elapsed / time_limit;
            T = T_start * pow(T_end / T_start, progress);
        }
        counter++;

        // Pick two distinct random indices (facilities)
        int u = dist_n(rng);
        int v = dist_n(rng);
        while (u == v) v = dist_n(rng);

        // Current locations
        int lu = p[u];
        int lv = p[v];

        // Compute Delta (Change in cost if we swap p[u] and p[v])
        long long delta = 0;

        // Contributions from u's edges
        // Outgoing from u: terms F[u][k] * D[p[u]][p[k]]
        for (int k : F_out[u]) {
            if (k == u || k == v) continue;
            int lk = p[k];
            // Remove old cost, add new cost
            if (D[lu][lk]) delta--;
            if (D[lv][lk]) delta++;
        }
        // Incoming to u: terms F[k][u] * D[p[k]][p[u]]
        for (int k : F_in[u]) {
            if (k == u || k == v) continue;
            int lk = p[k];
            if (D[lk][lu]) delta--;
            if (D[lk][lv]) delta++;
        }

        // Contributions from v's edges
        // Outgoing from v
        for (int k : F_out[v]) {
            if (k == u || k == v) continue;
            int lk = p[k];
            if (D[lv][lk]) delta--;
            if (D[lu][lk]) delta++;
        }
        // Incoming to v
        for (int k : F_in[v]) {
            if (k == u || k == v) continue;
            int lk = p[k];
            if (D[lk][lv]) delta--;
            if (D[lk][lu]) delta++;
        }

        // Interaction between u and v
        if (F_mat[u][v]) {
            // u->v edge. Old: D[lu][lv], New: D[lv][lu]
            if (D[lu][lv]) delta--;
            if (D[lv][lu]) delta++;
        }
        if (F_mat[v][u]) {
            // v->u edge. Old: D[lv][lu], New: D[lu][lv]
            if (D[lv][lu]) delta--;
            if (D[lu][lv]) delta++;
        }

        // Self loops
        if (F_mat[u][u]) {
            if (D[lu][lu]) delta--;
            if (D[lv][lv]) delta++;
        }
        if (F_mat[v][v]) {
            if (D[lv][lv]) delta--;
            if (D[lu][lu]) delta++;
        }

        // Decide acceptance
        if (delta < 0) {
            current_cost += delta;
            swap(p[u], p[v]);
        } else if (delta == 0) {
            // Always accept neutral moves to explore plateau
            swap(p[u], p[v]);
        } else {
            // Metropolis criterion
            if (dist_real(rng) < exp(-delta / T)) {
                current_cost += delta;
                swap(p[u], p[v]);
            }
        }
    }

    // Output result
    for (int i = 0; i < n; ++i) {
        cout << p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}