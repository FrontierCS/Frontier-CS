#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c; T sign = 1; T x = 0;
        c = getChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (!c) return false;
        }
        if (c == '-') { sign = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) {
            x = x * 10 + (c - '0');
        }
        out = x * sign;
        return true;
    }
} In;

struct Graph1Bits {
    int n, W;
    vector<vector<uint64_t>> bits; // bits[u][w]
    Graph1Bits(int n = 0) { init(n); }
    void init(int _n) {
        n = _n;
        W = (n + 63) >> 6;
        bits.assign(n, vector<uint64_t>(W, 0));
    }
    inline void addEdge(int u, int v) {
        bits[u][v >> 6] |= (1ULL << (v & 63));
        bits[v][u >> 6] |= (1ULL << (u & 63));
    }
    inline int hasEdge(int u, int v) const {
        return (bits[u][v >> 6] >> (v & 63)) & 1ULL;
    }
};

static inline uint64_t now_us() {
    using namespace std::chrono;
    return duration_cast<microseconds>(steady_clock::now().time_since_epoch()).count();
}

long long countMatches(const Graph1Bits &g1, const vector<vector<int>> &adj2, const vector<int> &P) {
    int n = (int)adj2.size();
    long long tot = 0;
    for (int u = 0; u < n; ++u) {
        const auto &nu = adj2[u];
        for (int v : nu) {
            if (v > u) {
                tot += g1.hasEdge(P[u], P[v]);
            }
        }
    }
    return tot;
}

long long deltaSwap_pair(int a, int b, const vector<vector<int>> &adj2, const Graph1Bits &g1, const vector<int> &P) {
    int pa = P[a], pb = P[b];
    long long delta = 0;
    // edges incident to 'a'
    const auto &Na = adj2[a];
    for (int v : Na) {
        int pv = (v == b ? pb : P[v]);
        int oldVal = g1.hasEdge(pa, pv);
        int newVal = g1.hasEdge(pb, (v == b ? pa : pv));
        delta += (newVal - oldVal);
    }
    // edges incident to 'b' (excluding (a,b) already counted)
    const auto &Nb = adj2[b];
    for (int u : Nb) {
        if (u == a) continue;
        int oldVal = g1.hasEdge(pb, P[u]);
        int newVal = g1.hasEdge(pa, P[u]);
        delta += (newVal - oldVal);
    }
    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!In.nextInt(n)) return 0;
    In.nextInt(m);

    Graph1Bits g1(n);
    vector<int> deg1(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v; In.nextInt(u); In.nextInt(v);
        --u; --v;
        if (u == v) continue;
        g1.addEdge(u, v);
        deg1[u]++; deg1[v]++;
    }

    vector<vector<int>> adj2(n);
    vector<int> deg2(n, 0);
    for (int i = 0; i < m; ++i) {
        int u, v; In.nextInt(u); In.nextInt(v);
        --u; --v;
        if (u == v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++; deg2[v]++;
    }

    // Precompute simple features
    vector<long long> sumNeiDeg1(n, 0), sumNeiDegSq1(n, 0);
    for (int u = 0; u < n; ++u) {
        long long s = 0, ss = 0;
        int W = g1.W;
        for (int w = 0; w < W; ++w) {
            uint64_t x = g1.bits[u][w];
            while (x) {
                int b = __builtin_ctzll(x);
                int v = (w << 6) + b;
                if (v < n) {
                    int d = deg1[v];
                    s += d;
                    ss += 1LL * d * d;
                }
                x &= x - 1;
            }
        }
        sumNeiDeg1[u] = s;
        sumNeiDegSq1[u] = ss;
    }

    vector<long long> sumNeiDeg2(n, 0), sumNeiDegSq2(n, 0);
    for (int u = 0; u < n; ++u) {
        long long s = 0, ss = 0;
        for (int v : adj2[u]) {
            int d = deg2[v];
            s += d;
            ss += 1LL * d * d;
        }
        sumNeiDeg2[u] = s;
        sumNeiDegSq2[u] = ss;
    }

    // Build initial permutations (seeds)
    vector<int> idx1(n), idx2(n);
    iota(idx1.begin(), idx1.end(), 0);
    iota(idx2.begin(), idx2.end(), 0);

    auto cmp1 = [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        if (sumNeiDeg1[a] != sumNeiDeg1[b]) return sumNeiDeg1[a] < sumNeiDeg1[b];
        if (sumNeiDegSq1[a] != sumNeiDegSq1[b]) return sumNeiDegSq1[a] < sumNeiDegSq1[b];
        return a < b;
    };
    auto cmp2 = [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        if (sumNeiDeg2[a] != sumNeiDeg2[b]) return sumNeiDeg2[a] < sumNeiDeg2[b];
        if (sumNeiDegSq2[a] != sumNeiDegSq2[b]) return sumNeiDegSq2[a] < sumNeiDegSq2[b];
        return a < b;
    };

    stable_sort(idx1.begin(), idx1.end(), cmp1);
    stable_sort(idx2.begin(), idx2.end(), cmp2);

    vector<vector<int>> seeds;
    vector<int> P0(n), P1(n), Pr(n);

    for (int k = 0; k < n; ++k) P0[idx2[k]] = idx1[k];
    for (int k = 0; k < n; ++k) P1[idx2[k]] = idx1[n - 1 - k];

    Pr.resize(n);
    iota(Pr.begin(), Pr.end(), 0);
    // Random shuffle Pr to a permutation
    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    shuffle(Pr.begin(), Pr.end(), rng);

    seeds.push_back(P0);
    seeds.push_back(P1);
    seeds.push_back(Pr);

    // Choose the best seed by matches
    long long bestScore = -1;
    vector<int> bestP;
    for (auto &Pseed : seeds) {
        long long sc = countMatches(g1, adj2, Pseed);
        if (sc > bestScore) {
            bestScore = sc;
            bestP = Pseed;
        }
    }

    // Local search with time limit
    // We set a fixed time budget for local search (in microseconds)
    const uint64_t LS_TIME_US = 1700000; // ~1.7s
    uint64_t start_time = now_us();
    uint64_t end_time = start_time + LS_TIME_US;

    vector<int> P = bestP;
    long long curScore = bestScore;

    auto rand01 = [&]() -> double {
        return (rng() >> 11) * (1.0 / 9007199254740992.0); // 53-bit
    };

    // Adaptive parameters
    int nK = min(20, max(2, n / 100)); // number of candidates per iteration
    if (n <= 200) nK = min(30, max(5, n - 1));
    double T0 = 1.0, Tend = 0.001;

    int stagnation = 0;

    while (now_us() < end_time) {
        // Cooling schedule
        double tfrac = double((now_us() - start_time)) / double(LS_TIME_US);
        if (tfrac > 1.0) tfrac = 1.0;
        double T = T0 * pow(Tend / T0, tfrac);

        int a = int(rng() % n);
        long long bestDelta = LLONG_MIN;
        int bestB = -1;

        for (int it = 0; it < nK; ++it) {
            int b = int(rng() % n);
            if (b == a) continue;
            long long d = deltaSwap_pair(a, b, adj2, g1, P);
            if (d > bestDelta) {
                bestDelta = d;
                bestB = b;
            }
        }

        if (bestB != -1) {
            bool accept = false;
            if (bestDelta > 0) accept = true;
            else {
                // Simulated annealing acceptance
                double prob = exp(double(bestDelta) / max(1e-12, T));
                if (rand01() < prob) accept = true;
            }
            if (accept) {
                swap(P[a], P[bestB]);
                curScore += bestDelta;
                stagnation = (bestDelta > 0) ? 0 : (stagnation + 1);
            } else {
                stagnation++;
            }
        } else {
            stagnation++;
        }

        // Occasional random kick to escape local minima
        if (stagnation > 2000) {
            for (int k = 0; k < 5; ++k) {
                int x = int(rng() % n), y = int(rng() % n);
                if (x == y) continue;
                long long d = deltaSwap_pair(x, y, adj2, g1, P);
                if (d >= 0 || rand01() < 0.05) {
                    swap(P[x], P[y]);
                    curScore += d;
                }
            }
            stagnation = 0;
        }
    }

    // Output permutation (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (P[i] + 1);
    }
    cout << '\n';
    return 0;
}