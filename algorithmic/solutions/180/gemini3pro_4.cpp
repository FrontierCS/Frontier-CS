#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <bitset>
#include <cmath>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 2005;

int n, m;
// G1 Adjacency Matrix for O(1) edge lookups.
// Using bitset for memory efficiency.
bitset<MAXN> adj1_mat[MAXN];

// Adjacency lists for iterating neighbors (used in WL init and SA)
vector<int> adj1_list[MAXN];
vector<int> adj2_list[MAXN];

// Permutation: p[i] is the vertex in G1 mapped to vertex i in G2
int p[MAXN];
int best_p[MAXN];
int max_score = -1;

// Hashing arrays for Weisfeiler-Lehman initialization
unsigned long long h1[MAXN], h2[MAXN];
unsigned long long next_h[MAXN];

// Compute WL-like hashes to characterize local topology of vertices
void compute_hashes(int k, const vector<int>* adj, unsigned long long* h) {
    // Initialize with degrees
    for (int i = 1; i <= n; ++i) {
        h[i] = adj[i].size();
    }
    
    // Refine hashes k times
    for (int iter = 0; iter < k; ++iter) {
        for (int i = 1; i <= n; ++i) {
            unsigned long long sum_neighbors = 0;
            // Summing neighbor hashes captures the neighborhood structure
            for (int neighbor : adj[i]) {
                sum_neighbors += h[neighbor];
            }
            // Mixing step with constants to generate new hash
            next_h[i] = h[i] * 19937ULL + sum_neighbors + 0x9e3779b97f4a7c15ULL; 
        }
        for (int i = 1; i <= n; ++i) h[i] = next_h[i];
    }
}

// Full score calculation O(M)
int calculate_score() {
    int s = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj2_list[u]) {
            if (u < v) { // Check each edge exactly once
                // Check if the mapped edge exists in G1
                if (adj1_mat[p[u]][p[v]]) {
                    s++;
                }
            }
        }
    }
    return s;
}

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    // Read G1
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj1_mat[u][v] = 1;
        adj1_mat[v][u] = 1;
        adj1_list[u].push_back(v);
        adj1_list[v].push_back(u);
    }

    // Read G2
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj2_list[u].push_back(v);
        adj2_list[v].push_back(u);
    }

    // --- Initialization Phase ---
    // Use WL Refinement to find a good initial mapping based on structure
    compute_hashes(4, adj1_list, h1);
    compute_hashes(4, adj2_list, h2);

    // Pair hash with original index to sort
    vector<pair<unsigned long long, int>> g1_nodes(n), g2_nodes(n);
    for (int i = 0; i < n; ++i) {
        g1_nodes[i] = {h1[i+1], i+1};
        g2_nodes[i] = {h2[i+1], i+1};
    }
    // Sort to align similar structures
    sort(g1_nodes.begin(), g1_nodes.end());
    sort(g2_nodes.begin(), g2_nodes.end());

    // Create initial permutation by mapping rank-to-rank
    for (int i = 0; i < n; ++i) {
        p[g2_nodes[i].second] = g1_nodes[i].second;
    }

    // Calculate initial score
    int current_score = calculate_score();
    max_score = current_score;
    for(int i=1; i<=n; ++i) best_p[i] = p[i];

    // --- Optimization Phase (Simulated Annealing) ---
    auto start_time = chrono::steady_clock::now();
    mt19937 rng(1337); 
    uniform_int_distribution<int> dist(1, n);
    uniform_real_distribution<double> dist_real(0.0, 1.0);

    double t = 1.0; 
    
    while (true) {
        // Run a batch to minimize overhead of clock checks
        for (int k = 0; k < 2500; ++k) {
            // Pick two distinct vertices to swap in G2
            int u = dist(rng);
            int v = dist(rng);
            while (u == v) v = dist(rng);

            // Calculate delta score efficiently
            int delta = 0;
            int pu = p[u];
            int pv = p[v];
            
            // Check neighbors of u in G2
            for (int neighbor : adj2_list[u]) {
                if (neighbor == v) continue; // edge (u, v) doesn't change validity since graph undirected
                int pn = p[neighbor];
                // Edge (u, neighbor) mapped to (pu, pn) -> (pv, pn)
                bool old_e = adj1_mat[pu][pn];
                bool new_e = adj1_mat[pv][pn];
                if (new_e != old_e) {
                    delta += (new_e ? 1 : -1);
                }
            }
            
            // Check neighbors of v in G2
            for (int neighbor : adj2_list[v]) {
                if (neighbor == u) continue;
                int pn = p[neighbor];
                // Edge (v, neighbor) mapped to (pv, pn) -> (pu, pn)
                bool old_e = adj1_mat[pv][pn];
                bool new_e = adj1_mat[pu][pn];
                if (new_e != old_e) {
                    delta += (new_e ? 1 : -1);
                }
            }
            
            // Metropolis acceptance criterion
            bool accept = false;
            if (delta >= 0) {
                accept = true;
            } else {
                if (dist_real(rng) < exp(delta / t)) {
                    accept = true;
                }
            }

            if (accept) {
                current_score += delta;
                swap(p[u], p[v]);
                if (current_score > max_score) {
                    max_score = current_score;
                    for(int i=1; i<=n; ++i) best_p[i] = p[i];
                    // If we found a perfect isomorphism, we can stop early
                    if (max_score == m) goto end_sa;
                }
            }
            
            // Cooling
            t *= 0.99995; 
            if (t < 1e-7) t = 1e-7;
        }
        
        // Time check (leave a small buffer before 2.0s limit, e.g. 1.90s)
        auto curr_time = chrono::steady_clock::now();
        if (chrono::duration<double>(curr_time - start_time).count() > 1.90) break;
    }
    
    end_sa:;

    // Output result
    for (int i = 1; i <= n; ++i) {
        cout << best_p[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}