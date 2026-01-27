#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2005;

bitset<MAXN> g1Adj[MAXN];
int deg1[MAXN], deg2[MAXN];
int sumNeiDeg1[MAXN], sumNeiDeg2[MAXN];
vector<int> neighbors2[MAXN];
int pcur[MAXN], pbest[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Read G1
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        g1Adj[u].set(v);
        g1Adj[v].set(u);
        ++deg1[u];
        ++deg1[v];
    }

    // Read G2
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        neighbors2[u].push_back(v);
        neighbors2[v].push_back(u);
        ++deg2[u];
        ++deg2[v];
    }

    // Compute neighbor degree sums for G1
    for (int u = 1; u <= n; ++u) {
        int s = 0;
        auto &row = g1Adj[u];
        for (int v = 1; v <= n; ++v) {
            if (row[v]) s += deg1[v];
        }
        sumNeiDeg1[u] = s;
    }

    // Compute neighbor degree sums for G2
    for (int u = 1; u <= n; ++u) {
        int s = 0;
        for (int v : neighbors2[u]) s += deg2[v];
        sumNeiDeg2[u] = s;
    }

    // Initial mapping by sorting invariants
    vector<int> ord1(n), ord2(n);
    for (int i = 0; i < n; ++i) {
        ord1[i] = i + 1;
        ord2[i] = i + 1;
    }

    sort(ord1.begin(), ord1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        if (sumNeiDeg1[a] != sumNeiDeg1[b]) return sumNeiDeg1[a] < sumNeiDeg1[b];
        return a < b;
    });

    sort(ord2.begin(), ord2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        if (sumNeiDeg2[a] != sumNeiDeg2[b]) return sumNeiDeg2[a] < sumNeiDeg2[b];
        return a < b;
    });

    for (int i = 0; i < n; ++i) {
        pcur[ord2[i]] = ord1[i];
    }

    // Compute initial matched edges
    long long matched = 0;
    for (int u = 1; u <= n; ++u) {
        int pu = pcur[u];
        for (int v : neighbors2[u]) {
            if (v > u) {
                int pv = pcur[v];
                if (g1Adj[pu][pv]) ++matched;
            }
        }
    }

    long long bestMatched = matched;
    for (int i = 1; i <= n; ++i) pbest[i] = pcur[i];

    // Simulated annealing parameters
    long long targetOps = 200000000LL;
    long long approxPerIter = max(1LL, (4LL * m + n - 1) / n);
    long long TOT_ITERS = targetOps / approxPerIter;
    if (TOT_ITERS < 10000LL) TOT_ITERS = 10000LL;
    if (TOT_ITERS > 3000000LL) TOT_ITERS = 3000000LL;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> distVertex(1, n);
    const double T0 = 1.0;
    const double Tend = 0.01;

    for (long long iter = 0; iter < TOT_ITERS; ++iter) {
        int a = distVertex(rng);
        int b = distVertex(rng);
        while (b == a) b = distVertex(rng);

        int pa = pcur[a];
        int pb = pcur[b];
        if (pa == pb) continue;

        int delta = 0;

        // Edges incident to a
        for (int y : neighbors2[a]) {
            if (y == b) continue;
            int py = pcur[y];
            delta += (int)g1Adj[pb][py] - (int)g1Adj[pa][py];
        }
        // Edges incident to b
        for (int y : neighbors2[b]) {
            if (y == a) continue;
            int py = pcur[y];
            delta += (int)g1Adj[pa][py] - (int)g1Adj[pb][py];
        }

        if (delta >= 0) {
            matched += delta;
            swap(pcur[a], pcur[b]);
            if (matched > bestMatched) {
                bestMatched = matched;
                for (int i = 1; i <= n; ++i) pbest[i] = pcur[i];
            }
        } else {
            double T = T0 + (Tend - T0) * (double)iter / (double)TOT_ITERS;
            double prob = exp((double)delta / T);
            double r = (double)rng() / (double)rng.max();
            if (prob > r) {
                matched += delta;
                swap(pcur[a], pcur[b]);
            }
        }
    }

    cout << pbest[1];
    for (int i = 2; i <= n; ++i) cout << ' ' << pbest[i];
    cout << '\n';

    return 0;
}