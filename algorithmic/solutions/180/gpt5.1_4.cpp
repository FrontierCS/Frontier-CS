#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2000 + 5;
static bool adj1[MAXN][MAXN];
static vector<int> g2[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Read G1
    vector<int> deg1(n + 1, 0), deg2(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        if (!adj1[u][v]) {
            adj1[u][v] = adj1[v][u] = true;
            deg1[u]++; deg1[v]++;
        }
    }

    // Read G2
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        g2[u].push_back(v);
        g2[v].push_back(u);
        deg2[u]++; deg2[v]++;
    }

    // Initial mapping by sorting vertices by degree
    vector<int> order1(n), order2(n);
    for (int i = 1; i <= n; i++) {
        order1[i - 1] = i;
        order2[i - 1] = i;
    }
    sort(order1.begin(), order1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        return a < b;
    });
    sort(order2.begin(), order2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        return a < b;
    });

    vector<int> p(n + 1);
    for (int i = 0; i < n; i++) {
        p[ order2[i] ] = order1[i];
    }

    // Compute initial matched edges
    long long matched = 0;
    for (int u = 1; u <= n; u++) {
        int pu = p[u];
        for (int v : g2[u]) {
            if (v > u) {
                if (adj1[pu][p[v]]) matched++;
            }
        }
    }

    // Hill climbing with random swaps
    mt19937_64 rng(712367821);
    long long it_limit = (50000000LL * n) / (4LL * m + 1);
    if (it_limit > 200000) it_limit = 200000;
    if (it_limit < 0) it_limit = 0;

    for (long long iter = 0; iter < it_limit; iter++) {
        int a = int(rng() % n) + 1;
        int b = int(rng() % n) + 1;
        while (b == a) b = int(rng() % n) + 1;

        if (deg2[a] == 0 && deg2[b] == 0) continue;

        int pa = p[a], pb = p[b];
        if (pa == pb) continue;

        long long delta = 0;

        const auto &nbrsA = g2[a];
        for (int x : nbrsA) {
            if (x == b) continue; // edge {a,b} has zero delta
            bool oldE = adj1[pa][p[x]];
            bool newE = adj1[pb][p[x]];
            if (oldE != newE) delta += (newE ? 1 : -1);
        }

        const auto &nbrsB = g2[b];
        for (int y : nbrsB) {
            if (y == a) continue;
            bool oldE = adj1[pb][p[y]];
            bool newE = adj1[pa][p[y]];
            if (oldE != newE) delta += (newE ? 1 : -1);
        }

        if (delta > 0) {
            p[a] = pb;
            p[b] = pa;
            matched += delta;
        }
    }

    // Output permutation
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}