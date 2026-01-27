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
    
    // Random generator
    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    
    // Initial coloring: greedy in random order minimizing conflicts with already colored neighbors
    vector<int> color(n, 0);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    for (int v : order) {
        array<int,3> cnt = {0,0,0};
        for (int u : adj[v]) {
            int c = color[u];
            if (c) cnt[c-1]++;
        }
        int best = 0;
        int bestVal = cnt[0];
        for (int k = 1; k < 3; ++k) {
            if (cnt[k] < bestVal || (cnt[k] == bestVal && uniform_int_distribution<int>(0,1)(rng))) {
                bestVal = cnt[k];
                best = k;
            }
        }
        color[v] = best + 1;
    }
    
    // Compute neighbor color counts degc[v][k]
    vector<array<int,3>> degc(n);
    for (int v = 0; v < n; ++v) degc[v] = {0,0,0};
    for (int v = 0; v < n; ++v) {
        int cv = color[v]-1;
        for (int u : adj[v]) {
            int cu = color[u]-1;
            if (cu >= 0) degc[v][cu]++;
        }
    }
    
    auto compute_gain = [&](int v, int &bestNew)->int {
        int cur = color[v]-1;
        int bestk = -1;
        int bestVal = INT_MAX;
        for (int k = 0; k < 3; ++k) {
            if (k == cur) continue;
            int val = degc[v][k];
            if (val < bestVal) { bestVal = val; bestk = k; }
            else if (val == bestVal && uniform_int_distribution<int>(0,1)(rng)) { bestk = k; }
        }
        if (bestk == -1) { bestNew = cur; return 0; }
        bestNew = bestk;
        int gain = degc[v][cur] - degc[v][bestk];
        return gain;
    };
    
    struct Item {
        int gain;
        int v;
        bool operator<(Item const& other) const {
            return gain < other.gain; // max-heap by gain
        }
    };
    priority_queue<Item> pq;
    for (int v = 0; v < n; ++v) {
        int bn;
        int g = compute_gain(v, bn);
        if (g > 0) pq.push({g, v});
    }
    
    // Hill-climbing: move vertices to colors that reduce conflicts
    vector<char> inQueue(n, 0); // optional; not strictly necessary as we recompute on pop
    while (!pq.empty()) {
        Item it = pq.top(); pq.pop();
        int v = it.v;
        int bestNew;
        int g = compute_gain(v, bestNew);
        if (g <= 0) continue;
        int oldc = color[v]-1;
        int newc = bestNew;
        if (newc == oldc) continue;
        // Apply move
        color[v] = newc + 1;
        // Update counts for neighbors
        for (int u : adj[v]) {
            degc[u][oldc]--;
            degc[u][newc]++;
            // Neighbor might now have improvement
            int bn;
            int gu = (color[u] ? (degc[u][color[u]-1] - min({degc[u][(color[u]%3)], degc[u][(color[u]+1)%3], degc[u][(color[u]+2)%3]})) : 0);
            // Recompute properly to avoid incorrect min across all three: use compute_gain
            int dummy;
            int g2 = compute_gain(u, dummy);
            if (g2 > 0) pq.push({g2, u});
        }
        // Reconsider v too
        int dummy;
        int gv = compute_gain(v, dummy);
        if (gv > 0) pq.push({gv, v});
    }
    
    // Output colors
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        int c = color[i];
        if (c < 1 || c > 3) c = 1;
        cout << c;
    }
    cout << '\n';
    return 0;
}