#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <cstring>
#include <numeric>

using namespace std;

// Constants matching the problem statement
const int MAX_N = 405;
const int MAX_M = 2005;
const int K = 100; // Number of Monte Carlo scenarios

struct EdgeInfo {
    int u, v, d, id;
};

int N, M;
int X[MAX_N], Y[MAX_N];
EdgeInfo edges[MAX_M];
// Stores {weight, edge_index} for each scenario, sorted by weight
vector<pair<int, int>> scenarios[K];
int real_parent[MAX_N];
int sim_parent[MAX_N];

// Disjoint Set Union (DSU) Find with path compression
int find_set(int* parent, int i) {
    int root = i;
    while (root != parent[root]) {
        root = parent[root];
    }
    int curr = i;
    while (curr != root) {
        int next = parent[curr];
        parent[curr] = root;
        curr = next;
    }
    return root;
}

// DSU Unite
bool unite_sets(int* parent, int i, int j) {
    int root_i = find_set(parent, i);
    int root_j = find_set(parent, j);
    if (root_i != root_j) {
        parent[root_i] = root_j;
        return true;
    }
    return false;
}

int dist_sq(int i, int j) {
    return (X[i] - X[j]) * (X[i] - X[j]) + (Y[i] - Y[j]) * (Y[i] - Y[j]);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < N; ++i) {
        cin >> X[i] >> Y[i];
    }

    for (int i = 0; i < M; ++i) {
        cin >> edges[i].u >> edges[i].v;
        edges[i].id = i;
        edges[i].d = (int)round(sqrt(dist_sq(edges[i].u, edges[i].v)));
    }

    // Initialize the DSU for the actual decisions
    iota(real_parent, real_parent + N, 0);

    // Pre-generate K scenarios of future edge weights
    mt19937 rng(1337);
    for (int s = 0; s < K; ++s) {
        scenarios[s].reserve(M);
        for (int i = 0; i < M; ++i) {
            // Generate weight uniformly in [d_i, 3*d_i]
            uniform_int_distribution<int> dist(edges[i].d, 3 * edges[i].d);
            scenarios[s].push_back({dist(rng), i});
        }
        // Sort edges by weight for efficient MST simulation
        sort(scenarios[s].begin(), scenarios[s].end());
    }

    // Process edges one by one
    for (int i = 0; i < M; ++i) {
        int l_i;
        cin >> l_i; // Read the actual length of the current edge
        
        int u = edges[i].u;
        int v = edges[i].v;

        // If vertices are already connected, we don't need this edge (to minimize cost)
        if (find_set(real_parent, u) == find_set(real_parent, v)) {
            cout << 0 << endl;
            continue;
        }

        int votes = 0;
        // Run simulations
        for (int s = 0; s < K; ++s) {
            // Copy current real DSU state to simulation DSU
            memcpy(sim_parent, real_parent, N * sizeof(int));
            
            bool cheaper_path_exists = false;
            
            // Iterate through future edges in this scenario
            for (auto& p : scenarios[s]) {
                int w = p.first;
                int idx = p.second;
                
                // We only consider future edges (idx > i)
                if (idx <= i) continue;
                
                // If we encounter an edge heavier or equal to current l_i, 
                // we can't form a STRICTLY cheaper path using only future edges
                if (w >= l_i) break;
                
                // Attempt to add this future edge
                if (unite_sets(sim_parent, edges[idx].u, edges[idx].v)) {
                    // Check if this edge connected u and v
                    if (find_set(sim_parent, u) == find_set(sim_parent, v)) {
                        cheaper_path_exists = true;
                        break;
                    }
                }
            }

            // If no cheaper path exists in the future for this scenario, we should take edge i
            if (!cheaper_path_exists) {
                votes++;
            }
        }

        // Majority vote
        if (votes > K / 2) {
            cout << 1 << endl;
            unite_sets(real_parent, u, v);
        } else {
            cout << 0 << endl;
        }
    }

    return 0;
}