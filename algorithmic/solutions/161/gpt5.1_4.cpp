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
    int find(int x) { return p[x] == x ? x : p[x] = find(p[x]); }
    bool unite(int a, int b) {
        a = find(a); b = find(b);
        if (a == b) return false;
        if (r[a] < r[b]) swap(a, b);
        p[b] = a;
        if (r[a] == r[b]) r[a]++;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;

    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) cin >> x[i] >> y[i];

    vector<int> u(M), v(M);
    vector<long long> w(M);
    for (int j = 0; j < M; ++j) {
        cin >> u[j] >> v[j] >> w[j];
        --u[j]; --v[j];
    }

    vector<long long> a(K), b(K);
    for (int k = 0; k < K; ++k) cin >> a[k] >> b[k];

    // Assign each resident to the nearest station
    const long long INF = (1LL << 60);
    vector<long long> maxDist2(N, 0);
    for (int k = 0; k < K; ++k) {
        long long best = INF;
        int best_i = 0;
        for (int i = 0; i < N; ++i) {
            long long dx = x[i] - a[k];
            long long dy = y[i] - b[k];
            long long ds = dx * dx + dy * dy;
            if (ds < best) {
                best = ds;
                best_i = i;
            }
        }
        if (best > maxDist2[best_i]) maxDist2[best_i] = best;
    }

    // Determine output strengths
    vector<int> P(N, 0);
    for (int i = 0; i < N; ++i) {
        long double rad = sqrtl((long double)maxDist2[i]);
        int Pi = (int)ceill(rad - 1e-9L);
        if (Pi < 0) Pi = 0;
        if (Pi > 5000) Pi = 5000;
        P[i] = Pi;
    }

    // Build MST to connect all stations
    vector<int> B(M, 0);
    vector<int> ord(M);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j) {
        return w[i] < w[j];
    });

    DSU dsu(N);
    int used = 0;
    for (int idx : ord) {
        if (dsu.unite(u[idx], v[idx])) {
            B[idx] = 1;
            if (++used == N - 1) break;
        }
    }

    // Output
    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for (int j = 0; j < M; ++j) {
        if (j) cout << ' ';
        cout << B[j];
    }
    cout << '\n';

    return 0;
}