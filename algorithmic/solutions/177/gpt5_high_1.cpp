#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // If no edges, any coloring works perfectly
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    // Initial greedy assignment
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });

    vector<int> col(n, -1);
    array<int,3> colorSize = {0,0,0};

    for (int v : order) {
        array<int,3> lc = {0,0,0};
        for (int u : adj[v]) {
            if (col[u] != -1) lc[col[u]]++;
        }
        // choose color minimizing conflicts with already colored neighbors
        int bestColor = 0;
        int bestVal = lc[0];
        for (int c = 1; c < 3; ++c) {
            if (lc[c] < bestVal || (lc[c] == bestVal && colorSize[c] < colorSize[bestColor])) {
                bestVal = lc[c];
                bestColor = c;
            }
        }
        col[v] = bestColor;
        colorSize[bestColor]++;
    }

    // Build neighbor color counts
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    for (int v = 0; v < n; ++v) {
        for (int u : adj[v]) {
            if (u > v) {
                cnt[v][col[u]]++;
                cnt[u][col[v]]++;
            }
        }
    }

    auto compute_gain_best = [&](int v) -> pair<int,int> {
        int c = col[v];
        int same = cnt[v][c];
        int bestC = 0;
        int minCnt = cnt[v][0];
        if (cnt[v][1] < minCnt) { minCnt = cnt[v][1]; bestC = 1; }
        if (cnt[v][2] < minCnt) { minCnt = cnt[v][2]; bestC = 2; }
        int gain = same - minCnt;
        return {gain, bestC};
    };

    // Priority queue for local improvement (gain, vertex)
    priority_queue<pair<int,int>> pq;
    for (int v = 0; v < n; ++v) {
        auto [g, bcol] = compute_gain_best(v);
        if (g > 0) pq.emplace(g, v);
    }

    while (!pq.empty()) {
        auto [g, v] = pq.top(); pq.pop();
        auto [curGain, bestC] = compute_gain_best(v);
        if (curGain <= 0) continue;
        int oldC = col[v];
        int newC = bestC;
        if (oldC == newC) continue; // Shouldn't happen since curGain > 0 implies min < same and min color != current
        col[v] = newC;

        // Update neighbors' counts due to v's color change
        for (int u : adj[v]) {
            cnt[u][oldC]--;
            cnt[u][newC]++;
        }

        // Reconsider v and neighbors
        {
            auto [gv, bc] = compute_gain_best(v);
            if (gv > 0) pq.emplace(gv, v);
        }
        for (int u : adj[v]) {
            auto [gu, bc] = compute_gain_best(u);
            if (gu > 0) pq.emplace(gu, u);
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (col[i] + 1);
    }
    cout << '\n';
    return 0;
}