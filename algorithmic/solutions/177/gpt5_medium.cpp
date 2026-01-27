#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<int> deg(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
        deg[u]++; deg[v]++;
    }
    
    vector<vector<int>> adj(n);
    adj.assign(n, {});
    for (int i = 0; i < n; ++i) adj[i].reserve(deg[i]);
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    edges.clear(); edges.shrink_to_fit();
    
    // RNG
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    seed ^= uint64_t(new int);
    std::mt19937_64 rng(seed);
    
    // Initial coloring: greedy by degree descending with random tie-breaks
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });
    vector<int> col(n, 0); // 1..3
    for (int v : order) {
        int cntc[3] = {0,0,0};
        for (int u : adj[v]) {
            if (col[u] != 0) cntc[col[u]-1]++;
        }
        int best = 0, bestVal = cntc[0];
        for (int c = 1; c < 3; ++c) {
            if (cntc[c] < bestVal) {
                bestVal = cntc[c];
                best = c;
            } else if (cntc[c] == bestVal) {
                if ((rng() & 1) == 0) { // random tie-break
                    best = c;
                    bestVal = cntc[c];
                }
            }
        }
        col[v] = best + 1;
    }
    
    // Neighbor color counts: cnt[v][colorIndex]
    vector<array<int,3>> cnt(n);
    for (int v = 0; v < n; ++v) cnt[v] = {0,0,0};
    for (int v = 0; v < n; ++v) {
        int cv = col[v] - 1;
        for (int u : adj[v]) {
            int cu = col[u] - 1;
            cnt[v][cu]++;
        }
    }
    
    auto compute_gain_and_color = [&](int v)->pair<int,int>{
        int cur = col[v] - 1;
        int oldSame = cnt[v][cur];
        int bestAltSame = INT_MAX;
        int bestColor = cur;
        for (int c = 0; c < 3; ++c) if (c != cur) {
            int val = cnt[v][c];
            if (val < bestAltSame) {
                bestAltSame = val;
                bestColor = c;
            }
        }
        int gain = oldSame - bestAltSame;
        return {gain, bestColor};
    };
    
    // Priority queue of improvements
    priority_queue<pair<int,int>> pq; // {gain, v}
    for (int v = 0; v < n; ++v) {
        auto [gain, bestC] = compute_gain_and_color(v);
        if (gain > 0) pq.push({gain, v});
    }
    
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.80; // seconds
    long long ops = 0;
    
    while (!pq.empty()) {
        if ((++ops & 2047) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > TIME_LIMIT) break;
        }
        auto [gain_old, v] = pq.top(); pq.pop();
        auto [gain, bestColor] = compute_gain_and_color(v);
        if (gain <= 0) continue;
        int oldc = col[v] - 1;
        int newc = bestColor;
        if (newc == oldc) continue;
        col[v] = newc + 1;
        // Update neighbors counts
        for (int u : adj[v]) {
            cnt[u][oldc]--;
            cnt[u][newc]++;
        }
        // Re-evaluate neighbors and push if they have improvements
        for (int u : adj[v]) {
            auto [g2, bc2] = compute_gain_and_color(u);
            if (g2 > 0) pq.push({g2, u});
        }
        // Optionally re-evaluate v as well (not necessary, but safe)
        auto [gv, bcv] = compute_gain_and_color(v);
        if (gv > 0) pq.push({gv, v});
    }
    
    // Output
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        int c = col[i];
        if (c < 1 || c > 3) c = int((rng() % 3) + 1);
        cout << c;
    }
    cout << '\n';
    return 0;
}