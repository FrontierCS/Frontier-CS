#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    bool nextInt(int &out) {
        char c;
        int sgn = 1;
        int x = 0;
        c = read();
        while (c <= ' ') {
            if (c == EOF) return false;
            c = read();
        }
        if (c == '-') {
            sgn = -1;
            c = read();
        }
        for (; c > ' '; c = read()) {
            x = x * 10 + (c - '0');
        }
        out = x * sgn;
        return true;
    }
};

static inline int getBit(const ull* row, int pos) {
    return (int)((row[pos >> 6] >> (pos & 63)) & 1ULL);
}
static inline void setBitVal(ull* row, int pos, int val) {
    ull mask = 1ULL << (pos & 63);
    if (val) row[pos >> 6] |= mask;
    else row[pos >> 6] &= ~mask;
}
static inline long long popcount_and(const ull* a, const ull* b, int W) {
    long long s = 0;
    for (int i = 0; i < W; ++i) s += __builtin_popcountll(a[i] & b[i]);
    return s;
}

struct RNG {
    uint64_t x;
    RNG() {
        uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
        x = t ^ 0x9e3779b97f4a7c15ULL;
        x ^= (x << 7);
        x ^= (x >> 9);
    }
    inline uint64_t next() {
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        return x * 2685821657736338717ULL;
    }
    inline int nextInt(int n) { return (int)(next() % (uint64_t)n); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    FastScanner fs;
    int n;
    if (!fs.nextInt(n)) {
        return 0;
    }
    int W = (n + 63) >> 6;
    vector<ull> Drow((size_t)n * W, 0), Dcol((size_t)n * W, 0);
    vector<ull> Frow((size_t)n * W, 0), Fcol((size_t)n * W, 0);
    vector<long long> Dout(n, 0), Din(n, 0), Fout(n, 0), Fin(n, 0);

    // Read D
    for (int i = 0; i < n; ++i) {
        ull* drow = &Drow[(size_t)i * W];
        for (int j = 0; j < n; ++j) {
            int v; fs.nextInt(v);
            if (v) {
                setBitVal(drow, j, 1);
                ull* dcol = &Dcol[(size_t)j * W];
                setBitVal(dcol, i, 1);
                Dout[i]++; Din[j]++;
            }
        }
    }
    // Read F
    for (int i = 0; i < n; ++i) {
        ull* frow = &Frow[(size_t)i * W];
        for (int j = 0; j < n; ++j) {
            int v; fs.nextInt(v);
            if (v) {
                setBitVal(frow, j, 1);
                ull* fcol = &Fcol[(size_t)j * W];
                setBitVal(fcol, i, 1);
                Fout[i]++; Fin[j]++;
            }
        }
    }

    // Initial permutation using degree heuristic
    vector<int> ordF(n), ordL(n);
    iota(ordF.begin(), ordF.end(), 0);
    iota(ordL.begin(), ordL.end(), 0);

    RNG rng;
    // Shuffle to break ties
    for (int i = n - 1; i > 0; --i) {
        int j = rng.nextInt(i + 1);
        swap(ordF[i], ordF[j]);
        j = rng.nextInt(i + 1);
        swap(ordL[i], ordL[j]);
    }

    vector<long long> wF(n), wD(n);
    for (int i = 0; i < n; ++i) wF[i] = Fout[i] + Fin[i];
    for (int i = 0; i < n; ++i) wD[i] = Dout[i] + Din[i];

    sort(ordF.begin(), ordF.end(), [&](int a, int b){
        if (wF[a] != wF[b]) return wF[a] > wF[b];
        return a < b;
    });
    sort(ordL.begin(), ordL.end(), [&](int a, int b){
        if (wD[a] != wD[b]) return wD[a] < wD[b];
        return a < b;
    });

    vector<int> p(n, 0);
    for (int i = 0; i < n; ++i) {
        p[ordF[i]] = ordL[i];
    }

    // Build Srow and Scol bitsets based on permutation p
    vector<ull> Srow((size_t)n * W, 0), Scol((size_t)n * W, 0);
    for (int l = 0; l < n; ++l) {
        ull* sRow = &Srow[(size_t)l * W];
        ull* dRow = &Drow[(size_t)l * W];
        for (int k = 0; k < n; ++k) {
            int loc = p[k];
            int val = getBit(dRow, loc);
            setBitVal(sRow, k, val);
        }
    }
    for (int l = 0; l < n; ++l) {
        ull* sCol = &Scol[(size_t)l * W];
        ull* dCol = &Dcol[(size_t)l * W];
        for (int k = 0; k < n; ++k) {
            int loc = p[k];
            int val = getBit(dCol, loc); // D[p[k]][l]
            setBitVal(sCol, k, val);
        }
    }

    // Compute initial cost
    long long cost = 0;
    for (int i = 0; i < n; ++i) {
        int l = p[i];
        ull* fr = &Frow[(size_t)i * W];
        ull* sr = &Srow[(size_t)l * W];
        cost += popcount_and(fr, sr, W);
    }

    auto compute_delta = [&](int a, int b) -> long long {
        if (a == b) return 0;
        int la = p[a], lb = p[b];
        ull* fra = &Frow[(size_t)a * W];
        ull* frb = &Frow[(size_t)b * W];
        ull* fca = &Fcol[(size_t)a * W];
        ull* fcb = &Fcol[(size_t)b * W];
        ull* s_la_row = &Srow[(size_t)la * W];
        ull* s_lb_row = &Srow[(size_t)lb * W];
        ull* s_la_col = &Scol[(size_t)la * W];
        ull* s_lb_col = &Scol[(size_t)lb * W];

        long long popA_lb = popcount_and(fra, s_lb_row, W);
        long long popA_la = popcount_and(fra, s_la_row, W);
        long long popB_lb = popcount_and(frb, s_lb_row, W);
        long long popB_la = popcount_and(frb, s_la_row, W);
        long long TR = (popA_lb - popA_la) - (popB_lb - popB_la);

        long long popcA_lb = popcount_and(fca, s_lb_col, W);
        long long popcA_la = popcount_and(fca, s_la_col, W);
        long long popcB_lb = popcount_and(fcb, s_lb_col, W);
        long long popcB_la = popcount_and(fcb, s_la_col, W);
        long long TC = (popcA_lb - popcA_la) - (popcB_lb - popcB_la);

        ull* d_la = &Drow[(size_t)la * W];
        ull* d_lb = &Drow[(size_t)lb * W];
        int D_lb_lb = getBit(d_lb, lb);
        int D_la_la = getBit(d_la, la);
        int D_lb_la = getBit(d_lb, la);
        int D_la_lb = getBit(d_la, lb);
        int c = D_lb_lb + D_la_la - D_lb_la - D_la_lb;

        int Faa = getBit(&Frow[(size_t)a * W], a);
        int Fbb = getBit(&Frow[(size_t)b * W], b);
        int Fab = getBit(&Frow[(size_t)a * W], b);
        int Fba = getBit(&Frow[(size_t)b * W], a);
        int t = Faa + Fbb - Fab - Fba;

        long long delta = TR + TC + (long long)c * (long long)t;
        return delta;
    };

    auto apply_swap = [&](int a, int b) {
        if (a == b) return;
        int la = p[a], lb = p[b];
        // Update Srow and Scol at bits a and b for all l
        for (int l = 0; l < n; ++l) {
            ull* sRow = &Srow[(size_t)l * W];
            ull* dRow = &Drow[(size_t)l * W];
            int valA = getBit(dRow, lb);
            int valB = getBit(dRow, la);
            setBitVal(sRow, a, valA);
            setBitVal(sRow, b, valB);

            ull* sCol = &Scol[(size_t)l * W];
            ull* dCol = &Dcol[(size_t)l * W];
            int cvalA = getBit(dCol, lb);
            int cvalB = getBit(dCol, la);
            setBitVal(sCol, a, cvalA);
            setBitVal(sCol, b, cvalB);
        }
        // swap p[a], p[b]
        p[a] = lb;
        p[b] = la;
    };

    // Local search
    auto t_start = chrono::steady_clock::now();
    int64_t time_limit_ms;
    if (n <= 200) time_limit_ms = 1800;
    else if (n <= 600) time_limit_ms = 1800;
    else time_limit_ms = 1800;
    int64_t soft_end_ms = time_limit_ms;

    if (n <= 200) {
        bool improved = true;
        while (improved) {
            auto now = chrono::steady_clock::now();
            int64_t elapsed = (int64_t)chrono::duration_cast<chrono::milliseconds>(now - t_start).count();
            if (elapsed >= soft_end_ms) break;
            improved = false;
            for (int i = 0; i < n; ++i) {
                for (int j = i + 1; j < n; ++j) {
                    long long delta = compute_delta(i, j);
                    if (delta < 0) {
                        apply_swap(i, j);
                        cost += delta;
                        improved = true;
                        break;
                    }
                }
                if (improved) break;
                if ((i & 31) == 0) {
                    now = chrono::steady_clock::now();
                    elapsed = (int64_t)chrono::duration_cast<chrono::milliseconds>(now - t_start).count();
                    if (elapsed >= soft_end_ms) { improved = false; break; }
                }
            }
        }
    } else {
        // Randomized hill climbing
        const int BATCH = 2048;
        while (true) {
            auto now = chrono::steady_clock::now();
            int64_t elapsed = (int64_t)chrono::duration_cast<chrono::milliseconds>(now - t_start).count();
            if (elapsed >= soft_end_ms) break;
            for (int it = 0; it < BATCH; ++it) {
                int a = rng.nextInt(n);
                int b = rng.nextInt(n - 1);
                if (b >= a) b++;
                long long delta = compute_delta(a, b);
                if (delta < 0) {
                    apply_swap(a, b);
                    cost += delta;
                }
            }
        }
    }

    // Output permutation (1-based)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}