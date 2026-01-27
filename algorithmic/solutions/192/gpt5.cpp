#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    auto local_search = [&](vector<int>& part) -> long long {
        int N = part.size();
        vector<int> ext(N, 0);
        long long cut = 0;
        for (int i = 0; i < N; ++i) {
            int cnt = 0;
            for (int j : g[i]) if (part[j] != part[i]) ++cnt;
            ext[i] = cnt;
            cut += cnt;
        }
        cut /= 2;
        vector<int> delta(N);
        for (int i = 0; i < N; ++i) delta[i] = deg[i] - 2 * ext[i];
        priority_queue<pair<int,int>> pq;
        for (int i = 0; i < N; ++i) pq.push({delta[i], i});
        while (!pq.empty()) {
            auto [d, v] = pq.top(); pq.pop();
            if (d != delta[v]) continue;
            if (d <= 0) break;
            int oldPart = part[v];
            part[v] ^= 1;
            cut += d;
            int oldExt = ext[v];
            ext[v] = deg[v] - oldExt;
            delta[v] = -delta[v];
            pq.push({delta[v], v});
            for (int u : g[v]) {
                if (part[u] == oldPart) {
                    ext[u] += 1;
                    delta[u] -= 2;
                } else {
                    ext[u] -= 1;
                    delta[u] += 2;
                }
                pq.push({delta[u], u});
            }
        }
        return cut;
    };

    vector<int> bestPart(n, 0);
    long long bestCut = -1;

    // BFS layering initialization
    vector<int> init(n, -1);
    for (int i = 0; i < n; ++i) {
        if (init[i] != -1) continue;
        queue<int> q;
        init[i] = (rng() & 1);
        q.push(i);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (init[v] == -1) {
                    init[v] = init[u] ^ 1;
                    q.push(v);
                }
            }
        }
    }
    {
        vector<int> part = init;
        long long c = local_search(part);
        bestCut = c;
        bestPart = part;
    }

    // Random restarts
    int restarts = 20;
    for (int r = 0; r < restarts; ++r) {
        vector<int> part(n);
        for (int i = 0; i < n; ++i) part[i] = (rng() & 1);
        long long c = local_search(part);
        if (c > bestCut) {
            bestCut = c;
            bestPart = part;
        }
    }

    // Perturbation around the best solution
    int k = max(1, n / 20);
    int perturbIters = 20;
    for (int t = 0; t < perturbIters; ++t) {
        vector<int> cur = bestPart;
        for (int j = 0; j < k; ++j) {
            int idx = rng() % n;
            cur[idx] ^= 1;
        }
        long long c = local_search(cur);
        if (c > bestCut) {
            bestCut = c;
            bestPart = cur;
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << bestPart[i];
    }
    cout << '\n';
    return 0;
}