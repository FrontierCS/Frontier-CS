#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getch() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template <class T>
    bool nextInt(T &out) {
        char c;
        do {
            c = getch();
            if (!c) return false;
        } while (c <= ' ');
        bool neg = false;
        if (c == '-') {
            neg = true;
            c = getch();
        }
        long long val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = getch();
        }
        out = neg ? -val : val;
        return true;
    }
};

static inline uint64_t splitmix64_next(uint64_t &state) {
    uint64_t z = (state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    if (!fs.nextInt(n)) return 0;

    int W = (n + 63) >> 6;
    vector<uint64_t> Dbits((size_t)n * W, 0ULL);
    vector<int> degD_out(n, 0), degD_in(n, 0);

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x; fs.nextInt(x);
            if (x) {
                size_t idx = (size_t)i * W + ((unsigned)j >> 6);
                Dbits[idx] |= (1ULL << (j & 63));
                degD_out[i]++;
                degD_in[j]++;
            }
        }
    }

    vector<vector<int>> F_out(n), F_in(n);
    vector<int> degF_out(n, 0), degF_in(n, 0);
    long long E = 0;

    for (int i = 0; i < n; ++i) {
        // Optional small reserve to reduce reallocations a bit
        F_out[i].reserve(64);
        for (int j = 0; j < n; ++j) {
            int x; fs.nextInt(x);
            if (x) {
                F_out[i].push_back(j);
                F_in[j].push_back(i);
                degF_out[i]++;
                degF_in[j]++;
                E++;
            }
        }
    }

    auto getD = [&](int r, int c) -> int {
        size_t idx = (size_t)r * W + ((unsigned)c >> 6);
        return (int)((Dbits[idx] >> (c & 63)) & 1ULL);
    };

    // Initial permutation by degree-based sorting
    vector<int> ordF(n), ordD(n);
    iota(ordF.begin(), ordF.end(), 0);
    iota(ordD.begin(), ordD.end(), 0);

    uint64_t rngState = chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rnd = [&]() -> uint64_t { return splitmix64_next(rngState); };
    for (int i = n - 1; i > 0; --i) {
        int j = (int)(rnd() % (uint64_t)(i + 1));
        swap(ordF[i], ordF[j]);
        swap(ordD[i], ordD[j]);
    }

    vector<int> scoreF(n), scoreD(n);
    for (int i = 0; i < n; ++i) {
        scoreF[i] = degF_out[i] + degF_in[i];
        scoreD[i] = degD_out[i] + degD_in[i];
    }

    stable_sort(ordF.begin(), ordF.end(), [&](int a, int b) {
        if (scoreF[a] != scoreF[b]) return scoreF[a] > scoreF[b];
        if (degF_out[a] != degF_out[b]) return degF_out[a] > degF_out[b];
        return a < b;
    });
    stable_sort(ordD.begin(), ordD.end(), [&](int a, int b) {
        if (scoreD[a] != scoreD[b]) return scoreD[a] < scoreD[b];
        if (degD_out[a] != degD_out[b]) return degD_out[a] < degD_out[b];
        return a < b;
    });

    vector<int> P(n, -1), inv(n, -1);
    for (int k = 0; k < n; ++k) {
        int i = ordF[k];
        int j = ordD[k];
        P[i] = j;
        inv[j] = i;
    }

    auto compute_cost = [&]() -> long long {
        long long cost = 0;
        for (int i = 0; i < n; ++i) {
            int pi = P[i];
            const auto &row = F_out[i];
            for (int j : row) {
                int pj = P[j];
                cost += getD(pi, pj);
            }
        }
        return cost;
    };

    long long cost = compute_cost();

    // Local search: randomized pairwise swap improvements with early acceptance
    auto delta_swap = [&](int a, int b) -> long long {
        if (a == b) return 0;
        int pa = P[a], pb = P[b];
        long long delta = 0;

        // i = a
        const auto &outA = F_out[a];
        for (int j : outA) {
            int pj = P[j];
            int pj_new = (j == a ? pb : (j == b ? pa : pj));
            delta += getD(pb, pj_new) - getD(pa, pj);
        }
        // i = b
        const auto &outB = F_out[b];
        for (int j : outB) {
            int pj = P[j];
            int pj_new = (j == a ? pb : (j == b ? pa : pj));
            delta += getD(pa, pj_new) - getD(pb, pj);
        }
        // j = a, i != a,b
        const auto &inA = F_in[a];
        for (int i : inA) {
            if (i == a || i == b) continue;
            int pi = P[i];
            delta += getD(pi, pb) - getD(pi, pa);
        }
        // j = b, i != a,b
        const auto &inB = F_in[b];
        for (int i : inB) {
            if (i == a || i == b) continue;
            int pi = P[i];
            delta += getD(pi, pa) - getD(pi, pb);
        }
        return delta;
    };

    // Time-bounded improvement
    auto t_start = chrono::high_resolution_clock::now();
    const long long time_limit_ms = 1700; // time budget for whole program; modest for safety
    const long long improve_budget_ms = max(200LL, time_limit_ms - 600); // reserve time for IO and finalization
    auto deadline = t_start + chrono::milliseconds(improve_budget_ms);

    // Determine sample size based on density
    int avgdeg = (n > 0 ? (int)(E / max(1, n)) : 0);
    int K = 16;
    if (avgdeg > 800) K = 8;
    else if (avgdeg > 400) K = 12;
    else if (avgdeg > 200) K = 16;
    else K = min(32, n - 1);

    bool improved = true;
    int rounds = 0;
    while (improved) {
        improved = false;
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        for (int i = n - 1; i > 0; --i) {
            int j = (int)(rnd() % (uint64_t)(i + 1));
            swap(idx[i], idx[j]);
        }
        for (int ii = 0; ii < n; ++ii) {
            if (chrono::high_resolution_clock::now() > deadline) { improved = false; break; }
            int a = idx[ii];
            long long bestDelta = 0;
            int bestb = -1;
            for (int t = 0; t < K; ++t) {
                int b = (int)(rnd() % (uint64_t)n);
                if (b == a) continue;
                long long d = delta_swap(a, b);
                if (d < bestDelta) {
                    bestDelta = d;
                    bestb = b;
                    break; // early acceptance
                }
            }
            if (bestb != -1) {
                int pa = P[a], pb = P[bestb];
                swap(P[a], P[bestb]);
                inv[pa] = bestb;
                inv[pb] = a;
                cost += bestDelta;
                improved = true;
            }
        }
        rounds++;
        if (rounds >= 3) break; // limit rounds to keep runtime predictable
    }

    // Output permutation (1-based)
    // p[i] = location assigned to facility i
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (P[i] + 1);
    }
    cout << '\n';
    return 0;
}