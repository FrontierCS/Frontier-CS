#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2005;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    vector< bitset<MAXN> > adj1(n + 1);
    vector<vector<int>> adj2(n + 1);
    vector<int> deg1(n + 1), deg2(n + 1);

    // Read G1
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u < 1 || u > n || v < 1 || v > n || u == v) continue;
        adj1[u].set(v);
        adj1[v].set(u);
        ++deg1[u];
        ++deg1[v];
    }

    // Read G2
    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u < 1 || u > n || v < 1 || v > n || u == v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        ++deg2[u];
        ++deg2[v];
    }

    // Initial matching by degree (descending)
    vector<int> id1(n), id2(n);
    for (int i = 0; i < n; ++i) {
        id1[i] = i + 1;
        id2[i] = i + 1;
    }

    sort(id1.begin(), id1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        return a < b;
    });

    sort(id2.begin(), id2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        return a < b;
    });

    vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        int v2 = id2[i];
        int v1 = id1[i];
        p[v2] = v1;
    }

    // Compute initial matched edges
    long long matched = 0;
    for (int u = 1; u <= n; ++u) {
        int pu = p[u];
        for (int v : adj2[u]) {
            if (v > u) {
                if (adj1[pu][p[v]]) ++matched;
            }
        }
    }

    // Simple random hill-climbing
    static uint64_t seed = 88172645463325252ULL;
    auto nextRand = [&]() -> uint32_t {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        return (uint32_t)seed;
    };

    int maxIters = min(20000, n * 200);
    for (int iter = 0; iter < maxIters; ++iter) {
        int a = (nextRand() % n) + 1;
        int b = (nextRand() % n) + 1;
        if (a == b) continue;

        int pa = p[a];
        int pb = p[b];
        if (pa == pb) continue;

        long long delta = 0;

        // Edges incident to a
        for (int x : adj2[a]) {
            if (x == b) continue;
            int px = p[x];
            bool before = adj1[pa][px];
            bool after  = adj1[pb][px];
            if (after) {
                if (!before) ++delta;
            } else {
                if (before) --delta;
            }
        }

        // Edges incident to b
        for (int y : adj2[b]) {
            if (y == a) continue;
            int py = p[y];
            bool before = adj1[pb][py];
            bool after  = adj1[pa][py];
            if (after) {
                if (!before) ++delta;
            } else {
                if (before) --delta;
            }
        }

        if (delta > 0) {
            matched += delta;
            swap(p[a], p[b]);
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}