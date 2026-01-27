#include <bits/stdc++.h>
using namespace std;

static inline void buildCounts(const vector<pair<int,int>>& edges, const vector<int>& color, vector<array<int,3>>& cnt) {
    int n = (int)cnt.size();
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
    for (auto &e : edges) {
        int u = e.first, v = e.second;
        int cu = color[u], cv = color[v];
        cnt[u][cv]++;
        cnt[v][cu]++;
    }
}

static inline void improveColors(vector<int>& color, vector<array<int,3>>& cnt, const vector<vector<int>>& g) {
    int n = (int)g.size();
    deque<int> q;
    vector<char> inQ(n, 1);
    q.resize(n);
    for (int i = 0; i < n; ++i) q[i] = i;

    while (!q.empty()) {
        int v = q.front(); q.pop_front(); inQ[v] = 0;
        int oldc = color[v];
        int best = 0;
        int bestCount = cnt[v][0];
        for (int c = 1; c < 3; ++c) {
            if (cnt[v][c] < bestCount) {
                best = c; bestCount = cnt[v][c];
            }
        }
        if (bestCount < cnt[v][oldc]) {
            int newc = best;
            for (int nb : g[v]) {
                cnt[nb][oldc]--;
                cnt[nb][newc]++;
                if (!inQ[nb]) { q.push_back(nb); inQ[nb] = 1; }
            }
            color[v] = newc;
        }
    }
}

static inline long long countConflicts(const vector<array<int,3>>& cnt, const vector<int>& color) {
    long long sum = 0;
    int n = (int)color.size();
    for (int i = 0; i < n; ++i) sum += cnt[i][color[i]];
    return sum / 2;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<vector<int>> g(n);
    g.reserve(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
        edges.emplace_back(u, v);
    }

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

    auto greedyInit = [&](vector<int>& color) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        sort(order.begin(), order.end(), [&](int a, int b){ return g[a].size() > g[b].size(); });
        color.assign(n, -1);
        for (int v : order) {
            int cntc[3] = {0,0,0};
            for (int nb : g[v]) {
                int c = color[nb];
                if (c >= 0) cntc[c]++;
            }
            int best = 0, bestCnt = cntc[0];
            for (int c = 1; c < 3; ++c) {
                if (cntc[c] < bestCnt) { best = c; bestCnt = cntc[c]; }
                else if (cntc[c] == bestCnt && (rng() & 1)) { best = c; bestCnt = cntc[c]; }
            }
            color[v] = best;
        }
    };

    auto randomInit = [&](vector<int>& color) {
        color.resize(n);
        for (int i = 0; i < n; ++i) color[i] = (int)(rng() % 3);
    };

    vector<int> bestColor(n, 0);
    long long bestConf = LLONG_MAX;

    // Run 1: greedy initialization
    {
        vector<int> color;
        greedyInit(color);
        vector<array<int,3>> cnt(n);
        buildCounts(edges, color, cnt);
        improveColors(color, cnt, g);
        long long conf = countConflicts(cnt, color);
        if (conf < bestConf) {
            bestConf = conf;
            bestColor = move(color);
        }
    }

    // Run 2: random initialization
    {
        vector<int> color;
        randomInit(color);
        vector<array<int,3>> cnt(n);
        buildCounts(edges, color, cnt);
        improveColors(color, cnt, g);
        long long conf = countConflicts(cnt, color);
        if (conf < bestConf) {
            bestConf = conf;
            bestColor = move(color);
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestColor[i] + 1);
    }
    cout << '\n';
    return 0;
}