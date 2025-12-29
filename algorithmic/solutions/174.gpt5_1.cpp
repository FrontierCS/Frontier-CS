#include <bits/stdc++.h>
using namespace std;

struct FastRNG {
    uint64_t x;
    static uint64_t splitmix64(uint64_t &y) {
        uint64_t z = (y += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    FastRNG() {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = splitmix64(seed);
    }
    inline uint64_t next() { return splitmix64(x); }
    inline uint32_t nextU32() { return (uint32_t)next(); }
    inline int nextInt(int l, int r) { return l + (int)(next() % (uint64_t)(r - l + 1)); }
    template <class T>
    inline void shuffleVec(vector<T>& a) {
        for (int i = (int)a.size() - 1; i > 0; --i) {
            int j = (int)(next() % (uint64_t)(i + 1));
            swap(a[i], a[j]);
        }
    }
};

static inline long long computeConflicts(const vector<int>& color, const vector<pair<int,int>>& edges) {
    long long b = 0;
    for (const auto &e : edges) {
        if (color[e.first] == color[e.second]) ++b;
    }
    return b;
}

static inline void greedyInitColors(vector<int>& color, const vector<vector<int>>& adj, FastRNG& rng) {
    int n = (int)adj.size();
    color.assign(n, -1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){ return adj[a].size() > adj[b].size(); });
    int groupSize[3] = {0,0,0};
    for (int u : order) {
        int cnt[3] = {0,0,0};
        for (int v : adj[u]) {
            int c = color[v];
            if (c >= 0) ++cnt[c];
        }
        int bestConf = min(cnt[0], min(cnt[1], cnt[2]));
        int cand[3]; int cc = 0;
        for (int k = 0; k < 3; ++k) if (cnt[k] == bestConf) cand[cc++] = k;
        // tie-break by current group sizes (prefer smaller)
        int minGroup = INT_MAX;
        int tmp[3]; int tc = 0;
        for (int i = 0; i < cc; ++i) minGroup = min(minGroup, groupSize[cand[i]]);
        for (int i = 0; i < cc; ++i) if (groupSize[cand[i]] == minGroup) tmp[tc++] = cand[i];
        int chosen = tmp[rng.nextInt(0, tc - 1)];
        color[u] = chosen;
        ++groupSize[chosen];
    }
}

static inline void randomInitColors(vector<int>& color, int n, FastRNG& rng) {
    color.resize(n);
    for (int i = 0; i < n; ++i) color[i] = rng.nextInt(0, 2);
}

static inline long long localOptimize(vector<int>& color, const vector<vector<int>>& adj, const vector<pair<int,int>>& edges, FastRNG& rng, int maxSweeps) {
    int n = (int)adj.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    for (int sweep = 0; sweep < maxSweeps; ++sweep) {
        // Shuffle order each sweep
        for (int i = n - 1; i > 0; --i) {
            int j = (int)(rng.next() % (uint64_t)(i + 1));
            swap(order[i], order[j]);
        }
        int changes = 0;
        for (int u : order) {
            int cnt0 = 0, cnt1 = 0, cnt2 = 0;
            const auto &nbrs = adj[u];
            for (int v : nbrs) {
                int c = color[v];
                if (c == 0) ++cnt0;
                else if (c == 1) ++cnt1;
                else ++cnt2;
            }
            int old = color[u];
            int oldConf = (old == 0) ? cnt0 : (old == 1) ? cnt1 : cnt2;
            int bestConf = cnt0;
            if (cnt1 < bestConf) bestConf = cnt1;
            if (cnt2 < bestConf) bestConf = cnt2;
            if (bestConf < oldConf) {
                int cand[3]; int cc = 0;
                if (cnt0 == bestConf) cand[cc++] = 0;
                if (cnt1 == bestConf) cand[cc++] = 1;
                if (cnt2 == bestConf) cand[cc++] = 2;
                int newColor = cand[rng.nextInt(0, cc - 1)];
                color[u] = newColor;
                ++changes;
            }
        }
        if (changes == 0) break;
    }
    return computeConflicts(color, edges);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> adj(n);
    adj.assign(n, {});
    vector<pair<int,int>> edges;
    edges.reserve((size_t)m);
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u < 0 || v < 0 || u >= n || v >= n || u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }
    m = (long long)edges.size();

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    FastRNG rng;

    int maxSweeps;
    int restarts;
    if (m > 300000) { maxSweeps = 12; restarts = 4; }
    else if (m > 100000) { maxSweeps = 14; restarts = 6; }
    else if (m > 50000) { maxSweeps = 16; restarts = 8; }
    else if (m > 10000) { maxSweeps = 18; restarts = 10; }
    else { maxSweeps = 24; restarts = 12; }

    vector<int> bestColor(n, 0);
    long long bestB = LLONG_MAX;

    // Greedy initialization + local search
    {
        vector<int> color;
        greedyInitColors(color, adj, rng);
        long long b = localOptimize(color, adj, edges, rng, maxSweeps);
        if (b < bestB) {
            bestB = b;
            bestColor = color;
        }
        if (bestB == 0) {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << (bestColor[i] + 1);
            }
            cout << '\n';
            return 0;
        }
    }

    // Random restarts + local search
    for (int r = 0; r < restarts; ++r) {
        vector<int> color;
        randomInitColors(color, n, rng);
        long long b = localOptimize(color, adj, edges, rng, maxSweeps);
        if (b < bestB) {
            bestB = b;
            bestColor = color;
        }
        if (bestB == 0) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestColor[i] + 1);
    }
    cout << '\n';
    return 0;
}