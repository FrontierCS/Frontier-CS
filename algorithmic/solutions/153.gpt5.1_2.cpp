#include <bits/stdc++.h>
using namespace std;

struct DSU {
    vector<int> p, r;
    DSU(int n = 0) { init(n); }
    void init(int n) {
        p.resize(n);
        r.assign(n, 0);
        iota(p.begin(), p.end(), 0);
    }
    int find(int x) {
        return p[x] == x ? x : p[x] = find(p[x]);
    }
    bool unite(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return false;
        if (r[a] < r[b]) swap(a, b);
        p[b] = a;
        if (r[a] == r[b]) ++r[a];
        return true;
    }
};

struct Edge {
    int id, u, v, d;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int firstA, firstB;
    if (!(cin >> firstA >> firstB)) return 0;

    int N, M;
    vector<pair<int,int>> coords;

    if (firstB > 800) { // likely "N M"
        N = firstA;
        M = firstB;
        coords.resize(N);
        for (int i = 0; i < N; ++i) {
            cin >> coords[i].first >> coords[i].second;
        }
    } else { // coordinates only, N and M are fixed
        N = 400;
        M = 1995;
        coords.resize(N);
        coords[0] = {firstA, firstB};
        for (int i = 1; i < N; ++i) {
            cin >> coords[i].first >> coords[i].second;
        }
    }

    vector<pair<int,int>> endpoints(M);
    for (int i = 0; i < M; ++i) {
        cin >> endpoints[i].first >> endpoints[i].second;
    }

    auto calc_d = [&](int u, int v) -> int {
        long long dx = coords[u].first - coords[v].first;
        long long dy = coords[u].second - coords[v].second;
        double dist = sqrt(double(dx * dx + dy * dy));
        return int(dist + 0.5);
    };

    vector<Edge> es;
    es.reserve(M);
    for (int i = 0; i < M; ++i) {
        int u = endpoints[i].first;
        int v = endpoints[i].second;
        int d = calc_d(u, v);
        es.push_back({i, u, v, d});
    }

    sort(es.begin(), es.end(), [](const Edge &a, const Edge &b) {
        return a.d < b.d;
    });

    vector<char> inMST(M, 0);
    DSU dsu(N);
    int cnt = 0;
    for (const auto &e : es) {
        if (dsu.unite(e.u, e.v)) {
            inMST[e.id] = 1;
            if (++cnt == N - 1) break;
        }
    }

    long long li;
    for (int i = 0; i < M; ++i) {
        if (!(cin >> li)) li = 0;
        int ans = inMST[i] ? 1 : 0;
        cout << ans << '\n';
        cout.flush();
    }

    return 0;
}