#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false); cin.tie(0);
    int n, m, k;
    double eps;
    cin >> n >> m >> k >> eps;

    vector<pair<int,int>> edges(m);
    for (int i = 0; i < m; i++) {
        cin >> edges[i].first >> edges[i].second;
    }

    // Simplify graph: remove duplicates and self-loops
    sort(edges.begin(), edges.end());
    edges.erase(unique(edges.begin(), edges.end()), edges.end());
    vector<vector<int>> adj(n + 1);
    for (auto& [u, v] : edges) {
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    int ideal = (n + k - 1) / k;               // ceil(n/k)
    int max_part_size = (int)((1.0 + eps) * ideal); // floor((1+eps)*ideal)

    vector<int> part(n + 1, -1);
    vector<int> part_size(k + 1, 0);

    // Random vertex order
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    shuffle(order.begin(), order.end(), rng);

    // Greedy assignment balancing edge cut and distinct neighbor parts
    for (int v : order) {
        vector<int> cnt(k + 1, 0);
        unordered_set<int> distinct_parts;
        for (int u : adj[v]) {
            if (part[u] != -1) {
                cnt[part[u]]++;
                distinct_parts.insert(part[u]);
            }
        }
        int best_part = -1;
        int best_score = -1e9;
        for (int p = 1; p <= k; p++) {
            if (part_size[p] < max_part_size) {
                int distinct_excluding_p = distinct_parts.size();
                if (distinct_parts.count(p)) distinct_excluding_p--;
                int score = cnt[p] - distinct_excluding_p;   // trade‑off EC vs CV
                if (score > best_score) {
                    best_score = score;
                    best_part = p;
                }
            }
        }
        part[v] = best_part;
        part_size[best_part]++;
    }

    // Iterative refinement for edge cut
    for (int iter = 0; iter < 5; iter++) {
        bool improved = false;
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int p = part[v];
            vector<int> cnt(k + 1, 0);
            for (int u : adj[v]) {
                cnt[part[u]]++;
            }
            int best_gain = 0;
            int best_q = p;
            for (int q = 1; q <= k; q++) {
                if (q == p) continue;
                if (part_size[q] >= max_part_size) continue;
                int gain = cnt[q] - cnt[p];
                if (gain > best_gain) {
                    best_gain = gain;
                    best_q = q;
                }
            }
            if (best_gain > 0) {
                part[v] = best_q;
                part_size[p]--;
                part_size[best_q]++;
                improved = true;
            }
        }
        if (!improved) break;
    }

    // Output partition
    for (int i = 1; i <= n; i++) {
        cout << part[i] << " \n"[i == n];
    }

    return 0;
}