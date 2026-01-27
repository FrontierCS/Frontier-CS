#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed=88172645463393265ull) { if (seed==0) seed=88172645463393265ull; x=seed; }
    inline uint64_t next() { x ^= x << 7; x ^= x >> 9; return x; }
    inline uint32_t next_u32() { return (uint32_t)next(); }
    inline int next_int(int l, int r) { return l + (int)(next_u32() % (uint32_t)(r-l+1)); }
    inline int next_bit() { return (int)(next_u32() & 1u); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if(!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> adj(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u==v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u,v);
    }
    m = (int)edges.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

    vector<unsigned char> best_s(n, 0);
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    auto compute_cut = [&](const vector<unsigned char>& s)->long long{
        long long c = 0;
        for (auto &e : edges) if (s[e.first] != s[e.second]) ++c;
        return c;
    };

    auto hill_climb = [&](vector<unsigned char> s)->pair<long long, vector<unsigned char>> {
        int N = n;
        vector<int> ext(N, 0);
        for (int v = 0; v < N; ++v) {
            int cnt = 0;
            for (int u : adj[v]) if (s[u] != s[v]) ++cnt;
            ext[v] = cnt;
        }
        vector<int> gain(N);
        for (int v = 0; v < N; ++v) gain[v] = deg[v] - 2 * ext[v];

        long long cut = 0;
        for (auto &e : edges) if (s[e.first] != s[e.second]) ++cut;

        priority_queue<pair<int,int>> pq;
        for (int v = 0; v < N; ++v) pq.emplace(gain[v], v);

        while (!pq.empty()) {
            auto [g, v] = pq.top(); pq.pop();
            if (g != gain[v]) continue;
            if (g <= 0) break;

            unsigned char sv = s[v];
            s[v] ^= 1;
            cut += g;

            // Update ext and gains
            int old_ext_v = ext[v];
            ext[v] = deg[v] - ext[v];
            gain[v] = -g;
            pq.emplace(gain[v], v);

            for (int u : adj[v]) {
                bool beforeDiff = ( ((int)s[u]) != ((int)sv) );
                if (beforeDiff) {
                    // edge was cut, now uncut
                    ext[u] -= 1;
                    gain[u] += 2;
                } else {
                    // edge was uncut, now cut
                    ext[u] += 1;
                    gain[u] -= 2;
                }
                pq.emplace(gain[u], u);
            }
        }
        return {cut, move(s)};
    };

    XorShift64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ 0x9e3779b97f4a7c15ull);

    long long best_cut = -1;
    vector<unsigned char> s(n, 0);

    const double TIME_LIMIT = 0.9; // seconds
    auto t_start = chrono::high_resolution_clock::now();
    int restarts = 0;
    const int MAX_RESTARTS = 200;

    // Include one deterministic-ish start: all zeros then local optimize (will do nothing)
    {
        auto res = hill_climb(s);
        if (res.first > best_cut) {
            best_cut = res.first;
            best_s = move(res.second);
        }
        ++restarts;
    }

    while (restarts < MAX_RESTARTS) {
        auto now = chrono::high_resolution_clock::now();
        double elapsed = chrono::duration<double>(now - t_start).count();
        if (elapsed > TIME_LIMIT) break;

        for (int i = 0; i < n; ++i) s[i] = (unsigned char)rng.next_bit();
        auto res = hill_climb(s);
        if (res.first > best_cut) {
            best_cut = res.first;
            best_s = move(res.second);
        }
        ++restarts;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)best_s[i];
    }
    cout << '\n';
    return 0;
}