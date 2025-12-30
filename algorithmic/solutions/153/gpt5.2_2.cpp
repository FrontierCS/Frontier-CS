#include <bits/stdc++.h>
using namespace std;

struct DSU {
    int n;
    vector<int> p, sz;
    int comps;
    DSU() : n(0), comps(0) {}
    DSU(int n_) { init(n_); }
    void init(int n_) {
        n = n_;
        p.resize(n);
        sz.assign(n, 1);
        iota(p.begin(), p.end(), 0);
        comps = n;
    }
    int find(int a) {
        while (p[a] != a) {
            p[a] = p[p[a]];
            a = p[a];
        }
        return a;
    }
    bool same(int a, int b) { return find(a) == find(b); }
    bool unite(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return false;
        if (sz[a] < sz[b]) swap(a, b);
        p[b] = a;
        sz[a] += sz[b];
        comps--;
        return true;
    }
};

static constexpr int N = 400;
static constexpr int M = 1995;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) {
        if (!(cin >> x[i] >> y[i])) return 0;
    }

    vector<int> u(M), v(M);
    for (int i = 0; i < M; i++) {
        cin >> u[i] >> v[i];
    }

    vector<int> d(M);
    for (int i = 0; i < M; i++) {
        long long dx = x[u[i]] - x[v[i]];
        long long dy = y[u[i]] - y[v[i]];
        double dist = sqrt(double(dx * dx + dy * dy));
        d[i] = (int)llround(dist);
        if (d[i] <= 0) d[i] = 1;
    }

    // Decompose edges into 5 spanning trees by repeated Kruskal (mirrors generator idea).
    vector<int> rank5(M, 4);
    vector<char> used(M, 0);
    for (int iter = 0; iter < 5; iter++) {
        vector<int> idx;
        idx.reserve(M);
        for (int i = 0; i < M; i++) if (!used[i]) idx.push_back(i);
        sort(idx.begin(), idx.end(), [&](int a, int b) {
            if (d[a] != d[b]) return d[a] < d[b];
            return a < b;
        });
        DSU tmp(N);
        int cnt = 0;
        for (int id : idx) {
            if (tmp.unite(u[id], v[id])) {
                used[id] = 1;
                rank5[id] = iter;
                if (++cnt == N - 1) break;
            }
        }
        if (cnt != N - 1) {
            // Fallback: mark remaining as worst.
            for (int i = 0; i < M; i++) if (!used[i]) rank5[i] = 4;
            break;
        }
    }

    DSU dsu(N);
    vector<int> accepted;
    accepted.reserve(N - 1);

    auto canReject = [&](int i) -> bool {
        DSU t(N);
        for (int id : accepted) t.unite(u[id], v[id]);
        for (int j = i + 1; j < M; j++) t.unite(u[j], v[j]);
        return t.comps == 1;
    };

    for (int i = 0; i < M; i++) {
        int l;
        cin >> l;

        int a = u[i], b = v[i];
        int ans = 0;

        if (dsu.same(a, b)) {
            ans = 0;
        } else {
            bool okReject = canReject(i);
            if (!okReject) {
                ans = 1;
            } else {
                int r = rank5[i];
                double need = double(dsu.comps - 1) / double(M - i); // urgency
                double base = 1.10 + 2.15 * need;                   // 1.10 .. ~3.25 (capped later)
                double bonus = 0.55 * (4 - r) / 4.0;                // prefer earlier trees
                double thr = min(2.75, base + bonus);

                double ratio = double(l) / double(d[i]);
                if (ratio <= 1.18) ans = 1;           // very cheap
                else if (ratio <= thr) ans = 1;
                else ans = 0;
            }
        }

        cout << ans << '\n' << flush;
        if (ans == 1) {
            dsu.unite(a, b);
            accepted.push_back(i);
        }
    }

    return 0;
}