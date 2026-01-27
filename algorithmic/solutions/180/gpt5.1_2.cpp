#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2000;
bitset<MAXN + 1> adj1[MAXN + 1];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> g1(n + 1), g2(n + 1);
    vector<int> deg1(n + 1, 0), deg2(n + 1, 0);

    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g1[u].push_back(v);
        g1[v].push_back(u);
        deg1[u]++; deg1[v]++;
        adj1[u].set(v);
        adj1[v].set(u);
    }

    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g2[u].push_back(v);
        g2[v].push_back(u);
        deg2[u]++; deg2[v]++;
    }

    vector<long long> sum1(n + 1, 0), sum2(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        long long s = 0;
        for (int u : g1[v]) s += deg1[u];
        sum1[v] = s;
        s = 0;
        for (int u : g2[v]) s += deg2[u];
        sum2[v] = s;
    }

    struct Node {
        int id;
        int deg;
        long long w;
    };

    vector<Node> nodes1, nodes2;
    nodes1.reserve(n);
    nodes2.reserve(n);
    for (int v = 1; v <= n; ++v) {
        nodes1.push_back({v, deg1[v], sum1[v]});
        nodes2.push_back({v, deg2[v], sum2[v]});
    }

    auto cmp = [](const Node &a, const Node &b) {
        if (a.deg != b.deg) return a.deg > b.deg;
        if (a.w != b.w) return a.w > b.w;
        return a.id < b.id;
    };

    sort(nodes1.begin(), nodes1.end(), cmp);
    sort(nodes2.begin(), nodes2.end(), cmp);

    vector<int> p(n + 1);
    for (int k = 0; k < n; ++k) {
        p[nodes2[k].id] = nodes1[k].id;
    }

    long long curMatched = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : g2[u]) {
            if (v > u) {
                if (adj1[p[u]].test(p[v])) curMatched++;
            }
        }
    }

    long long avg_deg_int = (2LL * m + n - 1) / n;
    const long long MAX_TESTS = 40000000LL;
    long long ITER = MAX_TESTS / max(1LL, avg_deg_int);
    if (ITER < n) ITER = n;
    if (ITER > 200000) ITER = 200000;

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(1, n);

    for (long long it = 0; it < ITER; ++it) {
        int a = dist(rng);
        int b = dist(rng);
        if (a == b) {
            b = dist(rng);
            if (a == b) continue;
        }

        int pa = p[a], pb = p[b];
        if (pa == pb) continue;

        long long delta = 0;

        auto &na = g2[a];
        for (int x : na) {
            if (x == b) continue;
            int px = p[x];
            bool oldv = adj1[pa].test(px);
            bool newv = adj1[pb].test(px);
            if (oldv != newv) delta += newv ? 1 : -1;
        }

        auto &nb = g2[b];
        for (int y : nb) {
            if (y == a) continue;
            int py = p[y];
            bool oldv = adj1[pb].test(py);
            bool newv = adj1[pa].test(py);
            if (oldv != newv) delta += newv ? 1 : -1;
        }

        if (delta > 0) {
            swap(p[a], p[b]);
            curMatched += delta;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << p[i];
    }
    cout << '\n';

    return 0;
}