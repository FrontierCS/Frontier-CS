#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 2005;

// Adjacency matrix for G1 (fast lookup)
bool adj1[MAXN][MAXN];
// Adjacency list for G2 (fast iteration of neighbors)
vector<int> adj2[MAXN];

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Read G1 edges
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based indexing
        adj1[u][v] = adj1[v][u] = true;
    }

    // Read G2 edges
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based indexing
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    // --- Initialization Strategy ---
    // Match vertices based on their degrees.
    // Vertices with similar degrees in G2 and G1 are more likely to correspond.

    vector<pair<int, int>> deg1(n), deg2(n);
    for (int i = 0; i < n; ++i) {
        int d = 0;
        for (int j = 0; j < n; ++j) {
            if (adj1[i][j]) d++;
        }
        deg1[i] = {d, i};
    }
    for (int i = 0; i < n; ++i) {
        deg2[i] = {(int)adj2[i].size(), i};
    }

    // Sort by degree
    sort(deg1.begin(), deg1.end());
    sort(deg2.begin(), deg2.end());

    // Initial permutation p: p[u] = v means u in G2 maps to v in G1
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        p[deg2[i].second] = deg1[i].second;
    }

    // Calculate initial score
    long long current_score = 0;
    for (int u = 0; u < n; ++u) {
        for (int v : adj2[u]) {
            if (u < v) { // Consider each undirected edge once
                if (adj1[p[u]][p[v]]) {
                    current_score++;
                }
            }
        }
    }

    vector<int> best_p = p;
    long long best_score = current_score;

    // If perfect match found immediately
    if (best_score == m) {
        for (int i = 0; i < n; ++i) {
            cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
        return 0;
    }

    // --- Simulated Annealing ---
    mt19937 rng(1337);
    uniform_int_distribution<int> dist_n(0, n - 1);
    uniform_real_distribution<double> dist_r(0.0, 1.0);

    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.90; // Aiming slightly under 2s (typical limit)
    
    double t0 = 2.0;       // Initial temperature
    double t_end = 1e-4;   // Final temperature
    double t = t0;

    long long iter = 0;
    while (true) {
        // Periodically update temperature and check time
        if ((iter & 1023) == 0) {
            auto now = chrono::high_resolution_clock::now();
            chrono::duration<double> elapsed = now - start_time;
            double frac = elapsed.count() / time_limit;
            if (frac >= 1.0) break;
            // Exponential cooling schedule
            t = t0 * pow(t_end / t0, frac);
        }

        // Pick two distinct vertices to swap in the permutation
        int u = dist_n(rng);
        int v = dist_n(rng);
        while (u == v) v = dist_n(rng);

        int pu = p[u];
        int pv = p[v];
        
        int delta = 0;

        // Calculate change in score (delta) efficiently
        // Iterate neighbors of u in G2
        for (int neighbor : adj2[u]) {
            if (neighbor == v) continue; // The edge (u,v) itself doesn't change status
            int pn = p[neighbor];
            // Old contribution: edge (p[u], p[neighbor])
            if (adj1[pu][pn]) delta--;
            // New contribution: edge (p[v], p[neighbor])
            if (adj1[pv][pn]) delta++;
        }
        // Iterate neighbors of v in G2
        for (int neighbor : adj2[v]) {
            if (neighbor == u) continue;
            int pn = p[neighbor];
            // Old contribution: edge (p[v], p[neighbor])
            if (adj1[pv][pn]) delta--;
            // New contribution: edge (p[u], p[neighbor])
            if (adj1[pu][pn]) delta++;
        }

        // Acceptance criteria
        bool accept = false;
        if (delta >= 0) {
            accept = true;
        } else {
            // Metropolis criterion
            if (dist_r(rng) < exp(delta / t)) {
                accept = true;
            }
        }

        if (accept) {
            swap(p[u], p[v]);
            current_score += delta;
            
            if (current_score > best_score) {
                best_score = current_score;
                best_p = p;
                if (best_score == m) break; // Perfect score reached
            }
        }
        
        iter++;
    }

    // Output result
    for (int i = 0; i < n; ++i) {
        cout << best_p[i] + 1 << (i == n - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}