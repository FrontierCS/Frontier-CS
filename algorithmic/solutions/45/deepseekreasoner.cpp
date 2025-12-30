#include <iostream>
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <algorithm>
#include <random>
#include <cmath>
#include <cassert>

using namespace std;

struct Vertex {
    int part;                           // current part assignment (0..k-1)
    vector<int> neighbors;              // list of neighbor vertices (no duplicates)
    unordered_map<int, int> part_count; // neighbor part -> count
    int F;                              // number of distinct other parts among neighbors
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, k;
    double eps;
    cin >> n >> m >> k >> eps;

    // Build adjacency sets to remove self-loops and parallel edges
    vector<unordered_set<int>> adj_set(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // to 0‑based
        if (u == v) continue;
        adj_set[u].insert(v);
        adj_set[v].insert(u);
    }

    // Convert to adjacency lists
    vector<vector<int>> adj(n);
    for (int i = 0; i < n; ++i) {
        adj[i].assign(adj_set[i].begin(), adj_set[i].end());
    }

    // Balance constraint
    int ideal = (n + k - 1) / k; // ceil(n/k)
    int max_part_size = floor((1.0 + eps) * ideal);

    // Random number generator
    mt19937 rng(123456);

    // Initial balanced partition: distribute vertices evenly
    vector<int> part(n);
    vector<int> part_size(k, 0);
    {
        vector<int> targets(k);
        int base = n / k;
        int rem = n % k;
        for (int i = 0; i < k; ++i) {
            targets[i] = base + (i < rem ? 1 : 0);
        }
        vector<int> perm(n);
        iota(perm.begin(), perm.end(), 0);
        shuffle(perm.begin(), perm.end(), rng);
        int idx = 0;
        for (int p = 0; p < k; ++p) {
            for (int c = 0; c < targets[p]; ++c) {
                part[perm[idx]] = p;
                part_size[p]++;
                ++idx;
            }
        }
    }

    // Initialize vertices and compute part_count, F, part_comm
    vector<Vertex> vertices(n);
    vector<long long> part_comm(k, 0);
    for (int v = 0; v < n; ++v) {
        vertices[v].part = part[v];
        vertices[v].neighbors = adj[v];
        for (int u : adj[v]) {
            vertices[v].part_count[part[u]]++;
        }
        int F = 0;
        for (auto& entry : vertices[v].part_count) {
            if (entry.first != part[v]) F++;
        }
        vertices[v].F = F;
        part_comm[part[v]] += F;
    }

    // Compute initial edge cut (EC)
    long long initial_EC = 0;
    for (int v = 0; v < n; ++v) {
        for (int u : adj[v]) {
            if (u > v && part[u] != part[v]) initial_EC++;
        }
    }

    // Compute initial total communication volume (sum of F)
    long long initial_total_comm = 0;
    for (int p = 0; p < k; ++p) initial_total_comm += part_comm[p];

    // Weight for combining objectives
    double beta = (initial_total_comm == 0) ? 1.0 : (double)initial_EC / initial_total_comm;

    // Refinement loop
    const int MAX_ITER = 10;
    for (int iter = 0; iter < MAX_ITER; ++iter) {
        bool improved = false;
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);

        for (int v : order) {
            int A = vertices[v].part;
            // Candidate parts: those appearing in neighbors, plus one random part
            unordered_set<int> candidates;
            for (int u : vertices[v].neighbors) {
                candidates.insert(vertices[u].part);
            }
            candidates.insert(rng() % k);
            candidates.erase(A); // remove current part

            double best_gain = 0.0;
            int best_B = -1;

            // Precompute counts for v
            auto& v_count = vertices[v].part_count;
            int cA = (v_count.find(A) != v_count.end()) ? v_count[A] : 0;

            for (int B : candidates) {
                if (part_size[B] >= max_part_size) continue; // balance constraint

                int cB = (v_count.find(B) != v_count.end()) ? v_count[B] : 0;
                int gain_EC = cB - cA; // positive means EC decreases

                long long delta_total = 0;

                // Contribution of v itself
                int delta_F_v = 0;
                if (A != B) {
                    if (cA > 0) delta_F_v++;
                    if (cB > 0) delta_F_v--;
                }
                delta_total += delta_F_v;

                // Contributions of neighbors
                for (int u : vertices[v].neighbors) {
                    int P_u = vertices[u].part;
                    auto& u_count = vertices[u].part_count;
                    int old_count_A_u = (u_count.find(A) != u_count.end()) ? u_count[A] : 0;
                    int old_count_B_u = (u_count.find(B) != u_count.end()) ? u_count[B] : 0;

                    int delta_F_u = 0;
                    if (P_u != A) {
                        if (old_count_A_u == 1) delta_F_u--;
                    }
                    if (P_u != B) {
                        if (old_count_B_u == 0) delta_F_u++;
                    }
                    delta_total += delta_F_u;
                }

                double gain = gain_EC - beta * delta_total;
                if (gain > best_gain) {
                    best_gain = gain;
                    best_B = B;
                }
            }

            if (best_gain > 0 && best_B != -1) {
                // Apply move: v from A to best_B
                int B = best_B;

                // Update part_count of neighbors and their F, part_comm
                for (int u : vertices[v].neighbors) {
                    int P_u = vertices[u].part;
                    auto& u_count = vertices[u].part_count;
                    int old_count_A_u = (u_count.find(A) != u_count.end()) ? u_count[A] : 0;
                    int old_count_B_u = (u_count.find(B) != u_count.end()) ? u_count[B] : 0;

                    int delta_F_u = 0;
                    if (P_u != A) {
                        if (old_count_A_u == 1) delta_F_u--;
                    }
                    if (P_u != B) {
                        if (old_count_B_u == 0) delta_F_u++;
                    }

                    // Update u's part_count
                    u_count[A]--;
                    if (u_count[A] == 0) u_count.erase(A);
                    u_count[B]++;

                    // Update u.F and part_comm[P_u]
                    vertices[u].F += delta_F_u;
                    part_comm[P_u] += delta_F_u;
                }

                // Update v itself
                int old_F_v = vertices[v].F;
                int delta_F_v = 0;
                if (A != B) {
                    if (cA > 0) delta_F_v++;
                    if (cB > 0) delta_F_v--;
                }
                vertices[v].F += delta_F_v;
                vertices[v].part = B;
                part_comm[A] -= old_F_v;
                part_comm[B] += vertices[v].F;

                // Update part sizes
                part_size[A]--;
                part_size[B]++;

                improved = true;
            }
        }
        if (!improved) break;
    }

    // Output partition (1‑based)
    for (int v = 0; v < n; ++v) {
        cout << vertices[v].part + 1 << "\n";
    }

    return 0;
}