#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    // Use the actual number of edges read (in case of any anomalies)
    m = (int)edges.size();

    // Random initialization
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0, 2);

    vector<int> color(n);
    for (int i = 0; i < n; ++i) color[i] = dist(rng);

    // Count neighbors per color for each vertex
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        cnt[u][color[v]]++;
        cnt[v][color[u]]++;
    }

    // Initial conflicts
    long long conflicts = 0;
    for (auto &e : edges) {
        if (color[e.first] == color[e.second]) conflicts++;
    }

    // Local improvement using a queue
    deque<int> q;
    vector<char> inq(n, 0);
    for (int v = 0; v < n; ++v) {
        int c = color[v];
        int old_same = cnt[v][c];
        int best_c = 0;
        int best_val = cnt[v][0];
        for (int k = 1; k < 3; ++k) {
            if (cnt[v][k] < best_val) {
                best_val = cnt[v][k];
                best_c = k;
            }
        }
        if (best_val < old_same) {
            q.push_back(v);
            inq[v] = 1;
        }
    }

    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        inq[v] = 0;
        int c = color[v];
        int old_same = cnt[v][c];

        // Find best color
        int best_c = c;
        int best_val = old_same;
        for (int k = 0; k < 3; ++k) {
            if (cnt[v][k] < best_val) {
                best_val = cnt[v][k];
                best_c = k;
            }
        }
        if (best_c == c) continue; // no improvement

        // Apply move
        color[v] = best_c;
        conflicts += (best_val - old_same);

        // Update neighbors counts and schedule them
        for (int u : adj[v]) {
            cnt[u][c]--;
            cnt[u][best_c]++;
            if (!inq[u]) {
                // Check quickly if u could improve; push speculatively to avoid recomputation here
                inq[u] = 1;
                q.push_back(u);
            }
        }
        // No need to update cnt[v]; it counts neighbors' colors which didn't change
    }

    // Output colors in 1..3
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (color[i] + 1);
    }
    cout << '\n';
    return 0;
}