#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    inline int nextInt() {
        char c;
        int x = 0, sgn = 1;
        do { c = read(); if (!c) return 0; } while (c!='-' && (c<'0' || c>'9'));
        if (c=='-') { sgn = -1; c = read(); }
        for (; c>='0' && c<='9'; c=read()) x = x*10 + (c - '0');
        return x * sgn;
    }
};

struct Solver {
    int n;
    int mwords;
    vector<vector<uint64_t>> Drow, Dcol;
    vector<vector<uint64_t>> Frow, Fcol;
    vector<vector<uint64_t>> Rperm, Cperm;
    vector<int> rowSumD, colSumD;
    vector<int> wout, win;
    vector<int> P, invP;

    inline int popcount_and(const vector<uint64_t>& A, const vector<uint64_t>& B) const {
        int s = 0;
        for (int k = 0; k < mwords; ++k) s += __builtin_popcountll(A[k] & B[k]);
        return s;
    }
    inline int getbit(const vector<uint64_t>& V, int idx) const {
        return (V[idx >> 6] >> (idx & 63)) & 1ULL;
    }
    inline void setbit(vector<uint64_t>& V, int idx) {
        V[idx >> 6] |= (1ULL << (idx & 63));
    }
    inline void swap_bits(vector<uint64_t>& V, int a, int b) {
        int wa = a >> 6, wb = b >> 6;
        uint64_t ma = 1ULL << (a & 63), mb = 1ULL << (b & 63);
        bool ba = (V[wa] & ma) != 0;
        bool bb = (V[wb] & mb) != 0;
        if (ba != bb) {
            V[wa] ^= ma;
            V[wb] ^= mb;
        }
    }

    long long compute_cost() const {
        long long cost = 0;
        for (int i = 0; i < n; ++i) {
            cost += popcount_and(Rperm[i], Drow[P[i]]);
        }
        return cost;
    }

    long long delta_swap(int i, int j) {
        int a = P[i], b = P[j];
        if (a == b || i == j) return 0;
        int s_rows_full = popcount_and(Rperm[i], Drow[b]) - popcount_and(Rperm[i], Drow[a])
                        - popcount_and(Rperm[j], Drow[b]) + popcount_and(Rperm[j], Drow[a]);
        int s_cols_full = popcount_and(Cperm[i], Dcol[b]) - popcount_and(Cperm[i], Dcol[a])
                        - popcount_and(Cperm[j], Dcol[b]) + popcount_and(Cperm[j], Dcol[a]);

        int D_ba = getbit(Drow[b], a);
        int D_aa = getbit(Drow[a], a);
        int D_bb = getbit(Drow[b], b);
        int D_ab = getbit(Drow[a], b);

        int F_ii = getbit(Frow[i], i);
        int F_jj = getbit(Frow[j], j);
        int F_ij = getbit(Frow[i], j);
        int F_ji = getbit(Frow[j], i);

        int rowcorr = (F_ii - F_ji) * (D_ba - D_aa) + (F_ij - F_jj) * (D_bb - D_ab);
        int colcorr = (F_ii - F_ij) * (D_ab - D_aa) + (F_ji - F_jj) * (D_bb - D_ba);
        int d2 = F_ii * (D_bb - D_aa) + F_jj * (D_aa - D_bb) + F_ij * (D_ba - D_ab) + F_ji * (D_ab - D_ba);

        long long delta = (long long)(s_rows_full - rowcorr) + (long long)(s_cols_full - colcorr) + (long long)d2;
        return delta;
    }

    void apply_swap(int i, int j) {
        int a = P[i], b = P[j];
        if (a == b) return;
        swap(P[i], P[j]);
        invP[a] = j;
        invP[b] = i;
        int wa = a >> 6, wb = b >> 6;
        uint64_t ma = 1ULL << (a & 63);
        uint64_t mb = 1ULL << (b & 63);
        for (int t = 0; t < n; ++t) {
            // Rperm
            bool ra = (Rperm[t][wa] & ma) != 0;
            bool rb = (Rperm[t][wb] & mb) != 0;
            if (ra != rb) {
                Rperm[t][wa] ^= ma;
                Rperm[t][wb] ^= mb;
            }
            // Cperm
            bool ca = (Cperm[t][wa] & ma) != 0;
            bool cb = (Cperm[t][wb] & mb) != 0;
            if (ca != cb) {
                Cperm[t][wa] ^= ma;
                Cperm[t][wb] ^= mb;
            }
        }
    }

    void solve() {
        FastScanner fs;
        n = fs.nextInt();
        mwords = (n + 63) >> 6;
        Drow.assign(n, vector<uint64_t>(mwords, 0));
        Dcol.assign(n, vector<uint64_t>(mwords, 0));
        Frow.assign(n, vector<uint64_t>(mwords, 0));
        Fcol.assign(n, vector<uint64_t>(mwords, 0));
        rowSumD.assign(n, 0);
        colSumD.assign(n, 0);
        wout.assign(n, 0);
        win.assign(n, 0);

        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int d = fs.nextInt();
                if (d) {
                    Drow[i][j >> 6] |= (1ULL << (j & 63));
                    Dcol[j][i >> 6] |= (1ULL << (i & 63));
                    rowSumD[i]++;
                    colSumD[j]++;
                }
            }
        }
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int f = fs.nextInt();
                if (f) {
                    Frow[i][j >> 6] |= (1ULL << (j & 63));
                    Fcol[j][i >> 6] |= (1ULL << (i & 63));
                    wout[i]++;
                    win[j]++;
                }
            }
        }

        vector<long long> s_fac(n);
        for (int i = 0; i < n; ++i) s_fac[i] = (long long)wout[i] + (long long)win[i];
        vector<long long> t_loc(n);
        for (int l = 0; l < n; ++l) t_loc[l] = (long long)rowSumD[l] + (long long)colSumD[l];

        vector<int> ord_fac(n), ord_loc(n);
        iota(ord_fac.begin(), ord_fac.end(), 0);
        iota(ord_loc.begin(), ord_loc.end(), 0);
        sort(ord_fac.begin(), ord_fac.end(), [&](int a, int b){
            if (s_fac[a] != s_fac[b]) return s_fac[a] > s_fac[b];
            return a < b;
        });
        sort(ord_loc.begin(), ord_loc.end(), [&](int a, int b){
            if (t_loc[a] != t_loc[b]) return t_loc[a] < t_loc[b];
            return a < b;
        });

        // Greedy assignment based on linear proxy
        P.assign(n, -1);
        invP.assign(n, -1);
        vector<char> used(n, 0);
        for (int idx = 0; idx < n; ++idx) {
            int i = ord_fac[idx];
            long long best = (1LL<<62);
            int bestl = -1;
            for (int l = 0; l < n; ++l) if (!used[l]) {
                long long sc = (long long)wout[i] * (long long)rowSumD[l] + (long long)win[i] * (long long)colSumD[l];
                if (sc < best) {
                    best = sc;
                    bestl = l;
                }
            }
            P[i] = bestl;
            invP[bestl] = i;
            used[bestl] = 1;
        }

        // Build Rperm, Cperm aligned by locations
        Rperm.assign(n, vector<uint64_t>(mwords, 0));
        Cperm.assign(n, vector<uint64_t>(mwords, 0));
        for (int l = 0; l < n; ++l) {
            int j = invP[l];
            int wl = l >> 6;
            uint64_t ml = 1ULL << (l & 63);
            for (int i = 0; i < n; ++i) {
                if ((Frow[i][j >> 6] >> (j & 63)) & 1ULL) {
                    Rperm[i][wl] |= ml;
                }
                if ((Fcol[i][j >> 6] >> (j & 63)) & 1ULL) {
                    Cperm[i][wl] |= ml;
                }
            }
        }

        long long cost = compute_cost();

        // Improvement loop with time limit
        auto start = chrono::steady_clock::now();
        const double time_limit_ms = 1200.0; // milliseconds
        vector<int> posLoc(n, 0);
        for (int k = 0; k < n; ++k) posLoc[ord_loc[k]] = k;

        int K = min(n, 32);
        vector<int> topLocs(K), botLocs(K);
        for (int k = 0; k < K; ++k) topLocs[k] = ord_loc[k];
        for (int k = 0; k < K; ++k) botLocs[k] = ord_loc[n - 1 - k];

        bool improved = true;
        while (improved) {
            improved = false;
            // Heavy facilities into top locations
            for (int id = 0; id < n; ++id) {
                auto now = chrono::steady_clock::now();
                double elapsed = chrono::duration<double, milli>(now - start).count();
                if (elapsed > time_limit_ms) break;

                int i = ord_fac[id];
                int a = P[i];
                if (posLoc[a] < K) continue;
                for (int b : topLocs) {
                    int j = invP[b];
                    if (i == j) continue;
                    long long d = delta_swap(i, j);
                    if (d < 0) {
                        apply_swap(i, j);
                        cost += d;
                        improved = true;
                        break;
                    }
                }
            }
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double, milli>(now - start).count();
            if (elapsed > time_limit_ms) break;

            // Light facilities out of top into bottom
            for (int id = n - 1; id >= 0; --id) {
                now = chrono::steady_clock::now();
                elapsed = chrono::duration<double, milli>(now - start).count();
                if (elapsed > time_limit_ms) break;

                int i = ord_fac[id];
                int a = P[i];
                if (posLoc[a] >= K) continue; // not in top
                for (int b : botLocs) {
                    int j = invP[b];
                    if (i == j) continue;
                    long long d = delta_swap(i, j);
                    if (d < 0) {
                        apply_swap(i, j);
                        cost += d;
                        improved = true;
                        break;
                    }
                }
            }
        }

        // Output permutation 1-indexed
        for (int i = 0; i < n; ++i) {
            if (i) printf(" ");
            printf("%d", P[i] + 1);
        }
        printf("\n");
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    Solver solver;
    solver.solve();
    return 0;
}