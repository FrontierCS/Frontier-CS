#include <bits/stdc++.h>
using namespace std;

static inline long long computeConflicts(const vector<uint8_t>& color, const vector<pair<int,int>>& edges) {
    long long b = 0;
    for (const auto& e : edges) {
        if (color[e.first] == color[e.second]) ++b;
    }
    return b;
}

static void local_search(vector<uint8_t>& color, const vector<vector<int>>& g, mt19937& rng, int maxSweeps, chrono::steady_clock::time_point endTime) {
    int n = (int)g.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    for (int iter = 0; iter < maxSweeps; ++iter) {
        if (chrono::steady_clock::now() > endTime) break;
        shuffle(order.begin(), order.end(), rng);
        int moves = 0;
        for (int u : order) {
            int cnt[3] = {0,0,0};
            for (int v : g[u]) {
                ++cnt[color[v]];
            }
            int c = color[u];
            int bestVal = cnt[0], bestC = 0;
            for (int col = 1; col < 3; ++col) {
                if (cnt[col] < bestVal) {
                    bestVal = cnt[col];
                    bestC = col;
                }
            }
            if (bestVal < cnt[c]) {
                color[u] = (uint8_t)bestC;
                ++moves;
            }
        }
        if (moves == 0) break;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<pair<int,int>> edges;
    edges.reserve(m);
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        edges.emplace_back(u, v);
        g[u].push_back(v);
        g[v].push_back(u);
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    auto startTime = chrono::steady_clock::now();
    double timeLimitSec = 1.7;
    auto endTime = startTime + chrono::duration<double>(timeLimitSec);

    // BFS-based initialization (depth mod 3)
    vector<uint8_t> color(n, 0);
    vector<int> dist(n, -1);
    for (int s = 0; s < n; ++s) {
        if (dist[s] != -1) continue;
        queue<int> q;
        dist[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
    }
    for (int i = 0; i < n; ++i) {
        if (dist[i] < 0) color[i] = (uint8_t)(i % 3);
        else color[i] = (uint8_t)(dist[i] % 3);
    }

    vector<uint8_t> bestColor = color;
    long long bestB = computeConflicts(bestColor, edges);

    // Local search from BFS init
    local_search(color, g, rng, 12, endTime);
    long long bNow = computeConflicts(color, edges);
    if (bNow < bestB) {
        bestB = bNow;
        bestColor = color;
    }

    // Random restarts within time budget
    while (chrono::steady_clock::now() < endTime) {
        // Random initialization
        for (int i = 0; i < n; ++i) bestColor[i] = (uint8_t)(rng() % 3);
        color = bestColor;
        local_search(color, g, rng, 8, endTime);
        bNow = computeConflicts(color, edges);
        if (bNow < bestB) {
            bestB = bNow;
            bestColor = color;
        }
        if (chrono::steady_clock::now() >= endTime) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)bestColor[i] + 1;
    }
    cout << '\n';
    return 0;
}