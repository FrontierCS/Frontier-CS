#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getcharFast() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    int nextInt() {
        char c;
        int x = 0, sgn = 1;
        do { c = getcharFast(); } while (c <= ' ');
        if (c == '-') { sgn = -1; c = getcharFast(); }
        for (; c > ' '; c = getcharFast()) x = x * 10 + (c - '0');
        return x * sgn;
    }
};

static inline int popcount_and(const uint64_t* __restrict a, const uint64_t* __restrict b, int W) {
    int s = 0;
    for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i] & b[i]);
    return s;
}
static inline int get_bit(const vector<uint64_t> &M, int W, int row, int col) {
    return (int)((M[(size_t)row * W + (col >> 6)] >> (col & 63)) & 1ULL);
}
static inline int get_bit_ptr(const uint64_t* row, int col) {
    return (int)((row[col >> 6] >> (col & 63)) & 1ULL);
}
static inline void toggle_two_bits_columnwise(vector<uint64_t>& B, int W, int n, int a, int b) {
    int wa = a >> 6, wb = b >> 6;
    uint64_t ma = 1ULL << (a & 63);
    uint64_t mb = 1ULL << (b & 63);
    for (int r = 0; r < n; ++r) {
        uint64_t &ca = B[(size_t)r * W + wa];
        uint64_t &cb = B[(size_t)r * W + wb];
        bool ba = (ca & ma) != 0;
        bool bb = (cb & mb) != 0;
        if (ba != bb) {
            ca ^= ma;
            cb ^= mb;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n = fs.nextInt();
    int W = (n + 63) >> 6;

    vector<uint64_t> D_rows((size_t)n * W, 0), F_rows((size_t)n * W, 0), F_cols((size_t)n * W, 0);

    // Read D
    for (int i = 0; i < n; ++i) {
        uint64_t* row = &D_rows[(size_t)i * W];
        for (int j = 0; j < n; ++j) {
            int x = fs.nextInt();
            if (x) row[j >> 6] |= 1ULL << (j & 63);
        }
    }
    // Read F
    for (int i = 0; i < n; ++i) {
        uint64_t* rrow = &F_rows[(size_t)i * W];
        for (int j = 0; j < n; ++j) {
            int x = fs.nextInt();
            if (x) {
                rrow[j >> 6] |= 1ULL << (j & 63);
                F_cols[(size_t)j * W + (i >> 6)] |= 1ULL << (i & 63);
            }
        }
    }

    // Degrees
    vector<int> degF(n, 0), degD(n, 0);
    for (int i = 0; i < n; ++i) {
        int s = 0;
        uint64_t* r = &F_rows[(size_t)i * W];
        for (int k = 0; k < W; ++k) s += __builtin_popcountll(r[k]);
        degF[i] = s;
    }
    for (int i = 0; i < n; ++i) {
        int s = 0;
        uint64_t* r = &D_rows[(size_t)i * W];
        for (int k = 0; k < W; ++k) s += __builtin_popcountll(r[k]);
        degD[i] = s;
    }

    // Initial permutation: sort facilities by degF desc, locations by degD asc
    vector<int> idxF(n), idxD(n);
    iota(idxF.begin(), idxF.end(), 0);
    iota(idxD.begin(), idxD.end(), 0);
    stable_sort(idxF.begin(), idxF.end(), [&](int a, int b) { if (degF[a] != degF[b]) return degF[a] > degF[b]; return a < b; });
    stable_sort(idxD.begin(), idxD.end(), [&](int a, int b) { if (degD[a] != degD[b]) return degD[a] < degD[b]; return a < b; });

    vector<int> p(n), pinv(n);
    for (int k = 0; k < n; ++k) {
        int i = idxF[k], j = idxD[k];
        p[i] = j;
        pinv[j] = i;
    }

    // Build B[u][j] = D[u][p(j)]
    vector<uint64_t> B((size_t)n * W, 0);
    for (int u = 0; u < n; ++u) {
        uint64_t* Brow = &B[(size_t)u * W];
        uint64_t* Drow = &D_rows[(size_t)u * W];
        for (int j = 0; j < n; ++j) {
            int l = p[j];
            if ((Drow[l >> 6] >> (l & 63)) & 1ULL) {
                Brow[j >> 6] |= 1ULL << (j & 63);
            }
        }
    }

    // Initial cost
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int u = p[i];
        uint64_t* Frow = &F_rows[(size_t)i * W];
        uint64_t* Brow = &B[(size_t)u * W];
        cost += popcount_and(Frow, Brow, W);
    }

    // Local search with time limit
    using clk = chrono::steady_clock;
    auto start_time = clk::now();
    const double TIME_LIMIT = 1.8; // seconds

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rng = [&]() -> uint64_t {
        seed += 0x9e3779b97f4a7c15ull;
        uint64_t z = seed;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
        return z ^ (z >> 31);
    };

    auto time_elapsed = [&]() -> double {
        return chrono::duration<double>(clk::now() - start_time).count();
    };

    auto delta_swap = [&](int a, int b) -> long long {
        if (a == b) return 0;
        int u = p[a], v = p[b];
        const uint64_t* FrowA = &F_rows[(size_t)a * W];
        const uint64_t* FrowB = &F_rows[(size_t)b * W];
        const uint64_t* FcolA = &F_cols[(size_t)a * W];
        const uint64_t* FcolB = &F_cols[(size_t)b * W];
        const uint64_t* Bu = &B[(size_t)u * W];
        const uint64_t* Bv = &B[(size_t)v * W];

        long long RA = popcount_and(FrowA, Bv, W) - popcount_and(FrowA, Bu, W);
        long long RB = popcount_and(FrowB, Bu, W) - popcount_and(FrowB, Bv, W);
        long long CA = popcount_and(FcolA, Bv, W) - popcount_and(FcolA, Bu, W);
        long long CB = popcount_and(FcolB, Bu, W) - popcount_and(FcolB, Bv, W);

        int Faa = (int)((FrowA[a >> 6] >> (a & 63)) & 1ULL);
        int Fbb = (int)((FrowB[b >> 6] >> (b & 63)) & 1ULL);
        int Fab = (int)((FrowA[b >> 6] >> (b & 63)) & 1ULL);
        int Fba = (int)((FrowB[a >> 6] >> (a & 63)) & 1ULL);

        const uint64_t* Du = &D_rows[(size_t)u * W];
        const uint64_t* Dv = &D_rows[(size_t)v * W];
        int Duu = (int)((Du[u >> 6] >> (u & 63)) & 1ULL);
        int Dvv = (int)((Dv[v >> 6] >> (v & 63)) & 1ULL);
        int Duv = (int)((Du[v >> 6] >> (v & 63)) & 1ULL);
        int Dvu = (int)((Dv[u >> 6] >> (u & 63)) & 1ULL);
        int diagDiff = (Dvv + Duu) - (Dvu + Duv);

        long long S = (long long)diagDiff * ((Faa + Fbb) - (Fab + Fba));

        return RA + RB + CA + CB + S;
    };

    int K = (n <= 300 ? n - 1 : max(16, min(64, n / 16)));
    if (K < 1) K = 1;

    // Random descent with sampled best-of-K partner
    while (time_elapsed() < TIME_LIMIT) {
        int a = (int)(rng() % n);
        int best_b = -1;
        long long best_delta = 0;
        for (int t = 0; t < K; ++t) {
            int b = (int)(rng() % n);
            if (b == a) continue;
            long long d = delta_swap(a, b);
            if (d < best_delta) {
                best_delta = d;
                best_b = b;
            }
        }
        if (best_b != -1) {
            int a2 = a, b2 = best_b;
            int u = p[a2], v = p[b2];

            // Update B by swapping columns a2 and b2
            toggle_two_bits_columnwise(B, W, n, a2, b2);

            // Update permutation
            p[a2] = v; p[b2] = u;
            pinv[u] = b2; pinv[v] = a2;

            cost += best_delta;
        }
    }

    // Output permutation 1-based
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}