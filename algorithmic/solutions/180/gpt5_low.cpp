#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;
    int L = (n + 63) >> 6;
    
    vector<vector<uint64_t>> adj1(n, vector<uint64_t>(L, 0));
    vector<vector<int>> adj2(n);
    vector<pair<int,int>> edges2;
    edges2.reserve(m);
    
    auto set_edge_bits = [&](vector<vector<uint64_t>>& adj, int u, int v){
        adj[u][v>>6] |= (uint64_t(1) << (v & 63));
        adj[v][u>>6] |= (uint64_t(1) << (u & 63));
    };
    for (long long i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        set_edge_bits(adj1, u, v);
    }
    for (long long i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        if (u < v) edges2.emplace_back(u, v);
        else edges2.emplace_back(v, u);
    }
    // In case of duplicates, but problem states none. Ensure edges2 unique:
    // Not necessary per statement.
    
    vector<int> deg1(n,0), deg2(n,0);
    for (int i = 0; i < n; ++i) {
        int d = 0;
        for (int w = 0; w < L; ++w) d += __builtin_popcountll(adj1[i][w]);
        deg1[i] = d;
        deg2[i] = (int)adj2[i].size();
    }
    // sum of neighbor degrees as a secondary signature
    vector<long long> sig1(n,0), sig2(n,0);
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        // For G1: traverse bits set
        for (int w = 0; w < L; ++w) {
            uint64_t x = adj1[i][w];
            while (x) {
                int b = __builtin_ctzll(x);
                int v = (w<<6) + b;
                if (v < n) s += deg1[v];
                x &= x - 1;
            }
        }
        sig1[i] = s;
        long long t = 0;
        for (int v : adj2[i]) t += deg2[v];
        sig2[i] = t;
    }
    
    vector<int> ord1(n), ord2(n);
    iota(ord1.begin(), ord1.end(), 0);
    iota(ord2.begin(), ord2.end(), 0);
    sort(ord1.begin(), ord1.end(), [&](int a, int b){
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        if (sig1[a] != sig1[b]) return sig1[a] < sig1[b];
        return a < b;
    });
    sort(ord2.begin(), ord2.end(), [&](int a, int b){
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        if (sig2[a] != sig2[b]) return sig2[a] < sig2[b];
        return a < b;
    });
    
    vector<int> p(n, -1), invp(n, -1);
    for (int i = 0; i < n; ++i) {
        int u2 = ord2[i];
        int v1 = ord1[i];
        p[u2] = v1;
        invp[v1] = u2;
    }
    
    auto has1 = [&](int u1, int v1)->int{
        return ( (adj1[u1][v1>>6] >> (v1 & 63)) & 1ULL ) ? 1 : 0;
    };
    
    long long matched = 0;
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        matched += has1(p[u], p[v]);
    }
    
    mt19937_64 rng(123456789);
    auto start_time = chrono::steady_clock::now();
    
    auto time_exceeded = [&](){
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start_time).count();
        return elapsed > 1.7; // seconds budget
    };
    
    auto delta_swap = [&](int a, int b)->long long{
        if (a == b) return 0;
        int pa = p[a], pb = p[b];
        if (pa == pb) return 0;
        long long delta = 0;
        // neighbors of a
        for (int x : adj2[a]) {
            if (x == b) continue;
            int px = p[x];
            delta += has1(pb, px);
            delta -= has1(pa, px);
        }
        // neighbors of b
        for (int x : adj2[b]) {
            if (x == a) continue;
            int px = p[x];
            delta += has1(pa, px);
            delta -= has1(pb, px);
        }
        // edge between a and b does not change contribution
        return delta;
    };
    
    int max_iters = max(2000, min(20000, n * 10));
    for (int iter = 0; iter < max_iters; ++iter) {
        if (time_exceeded()) break;
        int a = (int)(rng() % n);
        int b = (int)(rng() % n);
        if (a == b) continue;
        long long d = delta_swap(a, b);
        if (d > 0) {
            swap(p[a], p[b]);
            matched += d;
        }
    }
    
    // A simple greedy pass: try to improve by scanning pairs with similar degrees
    // limited effort to avoid TLE
    int attempts = 0;
    for (int a = 0; a < n && !time_exceeded(); ++a) {
        // try a few candidates b near a in degree order
        for (int t = 0; t < 8; ++t) {
            if (time_exceeded()) break;
            int b = (int)(rng() % n);
            if (a == b) continue;
            if (abs(deg2[a] - deg2[b]) + abs(deg1[p[a]] - deg1[p[b]]) > 6) continue;
            long long d = delta_swap(a, b);
            if (d > 0) {
                swap(p[a], p[b]);
                matched += d;
            }
            if (++attempts > 20000) break;
        }
        if (attempts > 20000) break;
    }
    
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}