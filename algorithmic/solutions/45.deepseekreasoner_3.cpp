#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m_orig, k;
    double eps;
    cin >> n >> m_orig >> k >> eps;

    // Build adjacency list, removing self-loops and parallel edges
    vector<vector<int>> adj(n+1);
    for (int i = 0; i < m_orig; i++) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 1; i <= n; i++) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    // Compute total edges after simplification
    long long total_edges = 0;
    for (int i = 1; i <= n; i++) total_edges += adj[i].size();
    total_edges /= 2;
    double avg_deg = (double)total_edges * 2.0 / n;

    // Balance parameters
    int ideal = (n + k - 1) / k; // ceil(n/k)
    int max_part_size = floor((1.0 + eps) * ideal);

    // Special case k==1
    if (k == 1) {
        for (int i = 0; i < n; i++) cout << "1 ";
        cout << endl;
        return 0;
    }

    // Random balanced initial partition
    vector<int> part(n+1);
    vector<int> part_size(k, 0);
    vector<int> capacity_left(k, max_part_size);
    vector<int> vertices(n);
    iota(vertices.begin(), vertices.end(), 1);
    random_shuffle(vertices.begin(), vertices.end());
    srand(time(0));

    for (int v : vertices) {
        int p;
        do {
            p = rand() % k;
        } while (capacity_left[p] == 0);
        part[v] = p;
        capacity_left[p]--;
        part_size[p]++;
    }

    // Helper vectors for counting neighbor parts
    vector<int> cnt(k, 0);
    vector<int> used_parts;
    used_parts.reserve(k);

    // Phase 1: minimize edge cut
    int passes1 = 10;
    for (int iter = 0; iter < passes1; iter++) {
        random_shuffle(vertices.begin(), vertices.end());
        bool changed = false;
        for (int v : vertices) {
            int P = part[v];
            // Count neighbors per part
            used_parts.clear();
            int internal_deg = 0;
            for (int u : adj[v]) {
                int p_u = part[u];
                if (cnt[p_u] == 0) used_parts.push_back(p_u);
                cnt[p_u]++;
                if (p_u == P) internal_deg++;
            }
            // Evaluate possible moves
            int best_delta = 0; // delta_EC for staying is 0
            int best_part = P;
            for (int Q : used_parts) {
                if (Q == P) continue;
                if (part_size[Q] >= max_part_size) continue;
                int new_internal = cnt[Q];
                int delta_EC = internal_deg - new_internal;
                if (delta_EC < best_delta) {
                    best_delta = delta_EC;
                    best_part = Q;
                }
            }
            // Clear cnt for next vertex
            for (int p : used_parts) cnt[p] = 0;

            if (best_part != P) {
                part[v] = best_part;
                part_size[P]--;
                part_size[best_part]++;
                changed = true;
            }
        }
        if (!changed) break;
    }

    // Phase 2: reduce communication volume
    int passes2 = 5;
    double gamma = avg_deg / 2.0; // trade-off parameter
    for (int iter = 0; iter < passes2; iter++) {
        random_shuffle(vertices.begin(), vertices.end());
        bool changed = false;
        for (int v : vertices) {
            int P = part[v];
            // Count neighbors per part
            used_parts.clear();
            int internal_deg = 0;
            for (int u : adj[v]) {
                int p_u = part[u];
                if (cnt[p_u] == 0) used_parts.push_back(p_u);
                cnt[p_u]++;
                if (p_u == P) internal_deg++;
            }
            // Compute current F(v)
            bool hasP = (cnt[P] > 0);
            int current_F = used_parts.size() - (hasP ? 1 : 0);
            // Evaluate moves
            double best_score = 0.0; // score for staying
            int best_part = P;
            for (int Q : used_parts) {
                if (Q == P) continue;
                if (part_size[Q] >= max_part_size) continue;
                int new_internal = cnt[Q];
                int delta_EC = internal_deg - new_internal;
                // Compute new F(v)
                bool hasQ = (cnt[Q] > 0);
                int new_F = used_parts.size() - (hasQ ? 1 : 0);
                int delta_F = new_F - current_F;
                double score = delta_EC + gamma * delta_F;
                if (score < best_score) {
                    best_score = score;
                    best_part = Q;
                }
            }
            // Clear cnt
            for (int p : used_parts) cnt[p] = 0;

            if (best_part != P) {
                part[v] = best_part;
                part_size[P]--;
                part_size[best_part]++;
                changed = true;
            }
        }
        if (!changed) break;
    }

    // Output partition (1-indexed part labels)
    for (int i = 1; i <= n; i++) {
        cout << part[i] + 1 << " ";
    }
    cout << endl;

    return 0;
}