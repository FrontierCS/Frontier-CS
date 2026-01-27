#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    adj.reserve(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Random initialization
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937 rng(seed);
    uniform_int_distribution<int> dist(0, 2);

    vector<uint8_t> col(n);
    for (int i = 0; i < n; ++i) col[i] = (uint8_t)dist(rng);

    // Count neighbors per color
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    for (int v = 0; v < n; ++v) {
        for (int u : adj[v]) {
            cnt[v][col[u]]++;
        }
    }

    // Compute initial conflicts
    long long conflicts_twice = 0;
    for (int v = 0; v < n; ++v) conflicts_twice += cnt[v][col[v]];
    long long conflicts = conflicts_twice / 2;

    auto apply_move = [&](int v, int to){
        int from = col[v];
        if (from == to) return;
        conflicts += (long long)cnt[v][to] - (long long)cnt[v][from];
        for (int u : adj[v]) {
            cnt[u][from]--;
            cnt[u][to]++;
        }
        col[v] = (uint8_t)to;
    };

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    // Local improvement by sweeps
    bool improved = true;
    int sweeps = 0;
    while (improved) {
        improved = false;
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int cur = col[v];
            int bestCol = cur;
            int bestVal = cnt[v][cur];
            for (int k = 0; k < 3; ++k) {
                if (k == cur) continue;
                if (cnt[v][k] < bestVal) {
                    bestVal = cnt[v][k];
                    bestCol = k;
                }
            }
            if (bestCol != cur) {
                int delta = bestVal - cnt[v][cur];
                if (delta < 0) {
                    apply_move(v, bestCol);
                    improved = true;
                }
            }
        }
        ++sweeps;
        if (sweeps > 1000) break; // safety guard (shouldn't be needed)
    }

    // Output colors 1..3
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)col[i] + 1;
    }
    cout << '\n';

    return 0;
}