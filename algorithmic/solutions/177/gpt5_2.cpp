#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t& x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
static uint64_t rng_state = (uint64_t)chrono::steady_clock::now().time_since_epoch().count();
static inline uint64_t rng64() { return splitmix64(rng_state); }
static inline int randint(int l, int r) { return l + (int)(rng64() % (uint64_t)(r - l + 1)); }
template <class T>
static inline void fast_shuffle(vector<T>& a) {
    for (int i = (int)a.size() - 1; i > 0; --i) {
        int j = (int)(rng64() % (uint64_t)(i + 1));
        swap(a[i], a[j]);
    }
}

struct Timer {
    chrono::steady_clock::time_point start, deadline;
    Timer(double ms) {
        start = chrono::steady_clock::now();
        deadline = start + chrono::milliseconds((long long)ms);
    }
    inline bool time_up() const {
        return chrono::steady_clock::now() > deadline;
    }
    inline long long elapsed_ms() const {
        return chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start).count();
    }
};

static vector<int> initial_bipartite_greedy(const vector<vector<int>>& g) {
    int n = (int)g.size();
    vector<int> color(n, -1);
    vector<int> parity(n, -1);
    vector<int> comp;
    comp.reserve(n);
    queue<int> q;

    for (int s = 0; s < n; ++s) {
        if (color[s] != -1) continue;
        comp.clear();
        bool bip = true;
        parity[s] = 0;
        q.push(s);
        comp.push_back(s);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int u : g[v]) {
                if (parity[u] == -1) {
                    parity[u] = parity[v] ^ 1;
                    q.push(u);
                    comp.push_back(u);
                } else if (parity[u] == parity[v]) {
                    bip = false;
                }
            }
        }
        if (bip) {
            for (int v : comp) {
                color[v] = parity[v]; // 0 or 1
            }
            for (int v : comp) parity[v] = -1;
        } else {
            // Greedy 3-coloring in this component
            vector<int> order = comp;
            sort(order.begin(), order.end(), [&](int a, int b){
                if (g[a].size() != g[b].size()) return g[a].size() > g[b].size();
                return (rng64() & 1);
            });
            for (int v : order) {
                int cnt[3] = {0,0,0};
                for (int u : g[v]) {
                    if (color[u] != -1) cnt[color[u]]++;
                }
                int mn = cnt[0], best = 0;
                for (int c = 1; c < 3; ++c) {
                    if (cnt[c] < mn) { mn = cnt[c]; best = c; }
                }
                // random tie-break among equal minima
                vector<int> opts;
                for (int c = 0; c < 3; ++c) if (cnt[c] == mn) opts.push_back(c);
                color[v] = opts[(int)(rng64() % opts.size())];
            }
            for (int v : comp) parity[v] = -1;
        }
    }
    return color;
}

static vector<int> initial_random(int n) {
    vector<int> col(n);
    for (int i = 0; i < n; ++i) col[i] = (int)(rng64() % 3ULL);
    return col;
}

static vector<int> initial_random_order_greedy(const vector<vector<int>>& g) {
    int n = (int)g.size();
    vector<int> col(n, -1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    fast_shuffle(order);
    for (int v : order) {
        int cnt[3] = {0,0,0};
        for (int u : g[v]) {
            if (col[u] != -1) cnt[col[u]]++;
        }
        int mn = cnt[0], best = 0;
        for (int c = 1; c < 3; ++c) if (cnt[c] < mn) { mn = cnt[c]; best = c; }
        vector<int> opts;
        for (int c = 0; c < 3; ++c) if (cnt[c] == mn) opts.push_back(c);
        col[v] = opts[(int)(rng64() % opts.size())];
    }
    return col;
}

static int local_improvement(vector<int>& col, const vector<vector<int>>& g, const vector<pair<int,int>>& edges, Timer& timer) {
    int n = (int)g.size();
    vector<array<int,3>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};

    int b = 0;
    for (const auto& e : edges) {
        int u = e.first, v = e.second;
        cnt[u][col[v]]++;
        cnt[v][col[u]]++;
        if (col[u] == col[v]) b++;
    }

    deque<int> q;
    vector<char> inq(n, 1);
    for (int i = 0; i < n; ++i) q.push_back(i);

    int iter = 0;
    while (!q.empty()) {
        if ((++iter & 1023) == 0 && timer.time_up()) break;
        int v = q.front(); q.pop_front(); inq[v] = 0;
        int cur = col[v];
        int s0 = cnt[v][cur];
        int bestc = cur;
        int mn = s0;
        for (int c = 0; c < 3; ++c) {
            if (cnt[v][c] < mn) { mn = cnt[v][c]; bestc = c; }
        }
        if (bestc != cur) {
            col[v] = bestc;
            b += (mn - s0);
            for (int u : g[v]) {
                cnt[u][cur]--;
                cnt[u][bestc]++;
                if (!inq[u]) { inq[u] = 1; q.push_back(u); }
            }
            // neighbors changed; v may benefit again after neighbors, but it will be pushed by neighbors' changes if needed
        }
    }

    return b;
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
        g[u].push_back(v);
        g[v].push_back(u);
        edges.emplace_back(u, v);
    }

    double base_time_ms = 1800.0;
    if (n > 50000 || m > 180000) base_time_ms = 1500.0; // conservative for larger instances
    Timer timer(base_time_ms);

    vector<int> best_col(n, 0);
    int best_b = INT_MAX;

    // Attempt 1: Bipartite-aware greedy init
    {
        vector<int> col = initial_bipartite_greedy(g);
        int b = local_improvement(col, g, edges, timer);
        if (b < best_b) { best_b = b; best_col = move(col); }
    }

    // Attempt 2: Random initialization
    if (!timer.time_up()) {
        vector<int> col = initial_random(n);
        int b = local_improvement(col, g, edges, timer);
        if (b < best_b) { best_b = b; best_col = move(col); }
    }

    // Attempt 3: Random-order greedy init
    if (!timer.time_up()) {
        vector<int> col = initial_random_order_greedy(g);
        int b = local_improvement(col, g, edges, timer);
        if (b < best_b) { best_b = b; best_col = move(col); }
    }

    // Optional extra random restarts if time allows
    for (int tries = 0; tries < 3 && !timer.time_up(); ++tries) {
        vector<int> col = initial_random(n);
        int b = local_improvement(col, g, edges, timer);
        if (b < best_b) { best_b = b; best_col = move(col); }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_col[i] + 1);
    }
    cout << '\n';
    return 0;
}