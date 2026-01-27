#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c; int sign = 1; int val = 0; c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) val = val * 10 + (c - '0');
        out = val * sign;
        return true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    int L = (n + 63) >> 6;

    vector<vector<uint64_t>> A1(n, vector<uint64_t>(L, 0));
    vector<vector<int>> G1(n), G2(n);
    G1.reserve(n); G2.reserve(n);

    auto set_edge = [&](int u, int v) {
        A1[u][v >> 6] |= (1ULL << (v & 63));
    };
    auto has_edge1 = [&](int u, int v) -> int {
        return (A1[u][v >> 6] >> (v & 63)) & 1ULL;
    };

    for (int i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        G1[u].push_back(v);
        G1[v].push_back(u);
        set_edge(u, v);
        set_edge(v, u);
    }
    for (int i = 0; i < m; ++i) {
        int u, v; fs.readInt(u); fs.readInt(v);
        --u; --v;
        if (u == v) continue;
        G2[u].push_back(v);
        G2[v].push_back(u);
    }

    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; ++i) {
        deg1[i] = (int)G1[i].size();
        deg2[i] = (int)G2[i].size();
    }

    vector<long long> sdeg1(n, 0), sdeg2(n, 0);
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int v : G1[i]) s += deg1[v];
        sdeg1[i] = s;
    }
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int v : G2[i]) s += deg2[v];
        sdeg2[i] = s;
    }

    vector<int> order1(n), order2(n);
    iota(order1.begin(), order1.end(), 0);
    iota(order2.begin(), order2.end(), 0);

    sort(order1.begin(), order1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        if (sdeg1[a] != sdeg1[b]) return sdeg1[a] > sdeg1[b];
        return a < b;
    });
    sort(order2.begin(), order2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        if (sdeg2[a] != sdeg2[b]) return sdeg2[a] > sdeg2[b];
        return a < b;
    });

    vector<int> P(n, 0);
    for (int i = 0; i < n; ++i) {
        P[order2[i]] = order1[i];
    }

    vector<int> c(n, 0);
    long long matchedEdges = 0;
    for (int u = 0; u < n; ++u) {
        int pu = P[u];
        int cu = 0;
        const auto &Nu = G2[u];
        for (int v : Nu) {
            cu += has_edge1(pu, P[v]);
        }
        c[u] = cu;
        matchedEdges += cu;
    }
    matchedEdges /= 2;

    vector<int> mis(n);
    for (int i = 0; i < n; ++i) mis[i] = deg2[i] - c[i];

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto rnd = [&](int mod) -> int { return (int)(rng() % mod); };

    auto deltaSwap = [&](int a, int b) -> long long {
        if (a == b) return 0;
        int u1 = P[a], v1 = P[b];
        long long delta = 0;
        const auto &Na = G2[a];
        for (int x : Na) {
            if (x == b) continue;
            delta += (has_edge1(v1, P[x]) - has_edge1(u1, P[x]));
        }
        const auto &Nb = G2[b];
        for (int y : Nb) {
            if (y == a) continue;
            delta += (has_edge1(u1, P[y]) - has_edge1(v1, P[y]));
        }
        return delta;
    };

    auto applySwap = [&](int a, int b, long long delta) {
        int u1 = P[a], v1 = P[b];

        const auto &Na = G2[a];
        for (int x : Na) {
            if (x == b) continue;
            c[x] += (has_edge1(P[x], v1) - has_edge1(P[x], u1));
            mis[x] = deg2[x] - c[x];
        }
        const auto &Nb = G2[b];
        for (int y : Nb) {
            if (y == a) continue;
            c[y] += (has_edge1(P[y], u1) - has_edge1(P[y], v1));
            mis[y] = deg2[y] - c[y];
        }

        P[a] = v1;
        P[b] = u1;

        int ca = 0, cb = 0;
        for (int x : Na) ca += has_edge1(P[a], P[x]);
        for (int y : Nb) cb += has_edge1(P[b], P[y]);

        c[a] = ca; c[b] = cb;
        mis[a] = deg2[a] - c[a];
        mis[b] = deg2[b] - c[b];

        matchedEdges += delta;
    };

    auto start = chrono::steady_clock::now();
    auto deadline = start + chrono::milliseconds(900);

    int K1 = 4;
    int K2 = 6;

    for (int iter = 0; ; ++iter) {
        if ((iter & 63) == 0) {
            if (chrono::steady_clock::now() > deadline) break;
        }

        int bestA = rnd(n);
        int bestMis = mis[bestA];
        for (int t = 1; t < K1; ++t) {
            int cand = rnd(n);
            if (mis[cand] > bestMis) {
                bestMis = mis[cand];
                bestA = cand;
            }
        }

        int a = bestA;
        if (deg2[a] == 0) continue;

        long long bestDelta = LLONG_MIN;
        int bestB = -1;
        for (int t = 0; t < K2; ++t) {
            int b = rnd(n);
            if (b == a) continue;
            long long d = deltaSwap(a, b);
            if (d > bestDelta) {
                bestDelta = d;
                bestB = b;
            }
        }

        if (bestB != -1 && bestDelta > 0) {
            applySwap(a, bestB, bestDelta);
        }
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (P[i] + 1);
    }
    cout << '\n';

    return 0;
}