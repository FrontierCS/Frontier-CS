#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

// Maximum size as per problem statement
const int MAXN = 2005;

// Use short to save memory and potentially improve cache usage
// D[i][j] is distance between location i and location j
// F[i][j] is flow between facility i and facility j
short D[MAXN][MAXN];
short F[MAXN][MAXN];

// p[i] = location assigned to facility i
// i is 0..n-1, p[i] is 0..n-1
int p[MAXN]; 
int n;

// Adjacency lists for Flow matrix to speed up delta calculation
// F is binary, so we store neighbors
vector<int> adjF_out[MAXN];
vector<int> adjF_in[MAXN];

// Full cost calculation O(N^2)
long long calculate_total_cost() {
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (F[i][j]) {
                cost += D[p[i]][p[j]];
            }
        }
    }
    return cost;
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    // Read D matrix
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> D[i][j];
        }
    }

    // Read F matrix and build adjacency lists
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> F[i][j];
            if (F[i][j]) {
                adjF_out[i].push_back(j);
                adjF_in[j].push_back(i);
            }
        }
    }

    // Heuristic initialization
    // Strategy: Minimize Cost = sum D * F.
    // Map facilities with HIGH flow degrees to locations with LOW distance degrees.
    // This assumes minimizing 1*1 occurrences.
    
    vector<pair<int, int>> degF(n), degD(n);
    for (int i = 0; i < n; ++i) {
        int d = 0;
        for (int j = 0; j < n; ++j) d += F[i][j] + F[j][i];
        degF[i] = {d, i};
    }
    for (int i = 0; i < n; ++i) {
        int d = 0;
        for (int j = 0; j < n; ++j) d += D[i][j] + D[j][i];
        degD[i] = {d, i};
    }

    // Sort: degF Descending, degD Ascending
    sort(degF.rbegin(), degF.rend()); 
    sort(degD.begin(), degD.end());

    for (int i = 0; i < n; ++i) {
        p[degF[i].second] = degD[i].second;
    }

    long long current_cost = calculate_total_cost();
    long long best_cost = current_cost;
    vector<int> best_p(n);
    for(int i=0; i<n; ++i) best_p[i] = p[i];

    // Simulated Annealing Parameters
    double t_start = 2.5;
    double t_end = 0.005;
    double temp = t_start;
    
    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.95; // seconds

    mt19937 rng(1337);
    uniform_int_distribution<int> dist(0, n - 1);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    int iter = 0;
    while (true) {
        // Check time every 2048 iterations
        if ((iter & 2047) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > time_limit) break;
            
            // Exponential cooling schedule based on time
            double ratio = elapsed.count() / time_limit;
            temp = t_start * pow(t_end / t_start, ratio);
        }
        iter++;

        // Pick two distinct facilities to swap locations
        int u = dist(rng);
        int v = dist(rng);
        while (u == v) {
            v = dist(rng);
        }

        int pu = p[u];
        int pv = p[v];

        // Calculate Delta cost efficiently
        long long delta = 0;

        // 1. Interaction terms between u and v
        // Subtract old terms
        delta -= (long long)D[pu][pu] * F[u][u];
        delta -= (long long)D[pv][pv] * F[v][v];
        delta -= (long long)D[pu][pv] * F[u][v];
        delta -= (long long)D[pv][pu] * F[v][u];

        // Add new terms (facility u is now at pv, v is now at pu)
        delta += (long long)D[pv][pv] * F[u][u];
        delta += (long long)D[pu][pu] * F[v][v];
        delta += (long long)D[pv][pu] * F[u][v];
        delta += (long long)D[pu][pv] * F[v][u];

        // 2. Interaction with other nodes k (k != u, k != v)
        // Only iterate over non-zero flow entries
        
        // Outgoing from u: F[u][k]
        for (int k : adjF_out[u]) {
            if (k == u || k == v) continue;
            // Old: u->k (dist p[u] to p[k])
            // New: u->k (dist p[v] to p[k])
            delta += ((long long)D[pv][p[k]] - D[pu][p[k]]);
        }
        // Incoming to u: F[k][u]
        for (int k : adjF_in[u]) {
            if (k == u || k == v) continue;
            delta += ((long long)D[p[k]][pv] - D[p[k]][pu]);
        }
        // Outgoing from v: F[v][k]
        for (int k : adjF_out[v]) {
            if (k == u || k == v) continue;
            delta += ((long long)D[pu][p[k]] - D[pv][p[k]]);
        }
        // Incoming to v: F[k][v]
        for (int k : adjF_in[v]) {
            if (k == u || k == v) continue;
            delta += ((long long)D[p[k]][pu] - D[p[k]][pv]);
        }

        // Acceptance criteria
        bool accept = false;
        if (delta < 0) {
            accept = true;
        } else {
            // Metropolis criterion
            if (exp(-delta / temp) > dist_prob(rng)) {
                accept = true;
            }
        }

        if (accept) {
            current_cost += delta;
            swap(p[u], p[v]);
            if (current_cost < best_cost) {
                best_cost = current_cost;
                for(int i=0; i<n; ++i) best_p[i] = p[i];
            }
        }
    }

    // Output result (1-based indices)
    for (int i = 0; i < n; ++i) {
        cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}