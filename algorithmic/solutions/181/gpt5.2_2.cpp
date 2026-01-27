#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

public:
    int nextInt() {
        char c;
        do {
            c = readChar();
            if (!c) return 0;
        } while (c <= ' ');
        int sgn = 1;
        if (c == '-') {
            sgn = -1;
            c = readChar();
        }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        return x * sgn;
    }

    int next01() {
        char c;
        do {
            c = readChar();
            if (!c) return 0;
        } while (c <= ' ');
        if (c == '0') return 0;
        if (c == '1') return 1;
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        return x;
    }
};

struct BitMat {
    int n = 0, B = 0;
    vector<uint64_t> a;
    BitMat() = default;
    BitMat(int n_, int B_) { init(n_, B_); }
    void init(int n_, int B_) {
        n = n_;
        B = B_;
        a.assign((size_t)n * (size_t)B, 0ULL);
    }
    inline uint64_t* row(int i) { return a.data() + (size_t)i * (size_t)B; }
    inline const uint64_t* row(int i) const { return a.data() + (size_t)i * (size_t)B; }
};

static inline int popcount_and(const uint64_t* x, const uint64_t* y, int B) {
    int s = 0;
    for (int k = 0; k < B; k++) s += __builtin_popcountll(x[k] & y[k]);
    return s;
}

static inline int getBit(const uint64_t* row, int idx, const vector<int>& widx, const vector<uint64_t>& bmask) {
    return (row[widx[idx]] & bmask[idx]) ? 1 : 0;
}

static inline void setBit(uint64_t* row, int idx, const vector<int>& widx, const vector<uint64_t>& bmask) {
    row[widx[idx]] |= bmask[idx];
}

static inline void setBitVal(uint64_t* row, int idx, int val, const vector<int>& widx, const vector<uint64_t>& bmask) {
    uint64_t m = bmask[idx];
    uint64_t &w = row[widx[idx]];
    if (val) w |= m;
    else w &= ~m;
}

struct XorShift64 {
    uint64_t s;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : s(seed ? seed : 88172645463325252ull) {}
    inline uint64_t nextU64() {
        uint64_t x = s;
        x ^= x << 7;
        x ^= x >> 9;
        return s = x;
    }
    inline int nextInt(int mod) { return (int)(nextU64() % (uint64_t)mod); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n = fs.nextInt();
    int B = (n + 63) >> 6;

    vector<int> widx(n);
    vector<uint64_t> bmask(n);
    for (int i = 0; i < n; i++) {
        widx[i] = i >> 6;
        bmask[i] = 1ULL << (i & 63);
    }

    BitMat D(n, B), Frow(n, B), Fcol(n, B);

    vector<int> dRowSum(n, 0), dColSum(n, 0);
    for (int i = 0; i < n; i++) {
        uint64_t* ri = D.row(i);
        int rs = 0;
        for (int j = 0; j < n; j++) {
            int v = fs.next01();
            if (v) {
                setBit(ri, j, widx, bmask);
                rs++;
                dColSum[j]++;
            }
        }
        dRowSum[i] = rs;
    }

    vector<int> fRowSum(n, 0), fColSum(n, 0);
    for (int i = 0; i < n; i++) {
        uint64_t* r = Frow.row(i);
        int rs = 0;
        for (int j = 0; j < n; j++) {
            int v = fs.next01();
            if (v) {
                setBit(r, j, widx, bmask);
                setBit(Fcol.row(j), i, widx, bmask);
                rs++;
                fColSum[j]++;
            }
        }
        fRowSum[i] = rs;
    }

    vector<int> distDeg(n), flowDeg(n);
    for (int i = 0; i < n; i++) {
        distDeg[i] = dRowSum[i] + dColSum[i];
        flowDeg[i] = fRowSum[i] + fColSum[i];
    }

    vector<int> facilities(n), locations(n);
    iota(facilities.begin(), facilities.end(), 0);
    iota(locations.begin(), locations.end(), 0);

    {
        XorShift64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
        stable_sort(facilities.begin(), facilities.end(), [&](int a, int b) {
            if (flowDeg[a] != flowDeg[b]) return flowDeg[a] > flowDeg[b];
            return rng.nextU64() < rng.nextU64();
        });
        stable_sort(locations.begin(), locations.end(), [&](int a, int b) {
            if (distDeg[a] != distDeg[b]) return distDeg[a] < distDeg[b];
            return rng.nextU64() < rng.nextU64();
        });
    }

    BitMat RowProj(n, B), ColProj(n, B);
    vector<int> locOfFac(n, -1), facAtLoc(n, -1);
    vector<char> usedLoc(n, 0);
    vector<int> mark(n, -1);
    int iterId = 0;

    XorShift64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() * 11400714819323198485ull);

    const int L = 60;
    const int R = 40;

    auto getD = [&](int r, int c) -> int {
        const uint64_t* rr = D.row(r);
        return (rr[widx[c]] & bmask[c]) ? 1 : 0;
    };
    auto getF = [&](int i, int j) -> int {
        const uint64_t* rr = Frow.row(i);
        return (rr[widx[j]] & bmask[j]) ? 1 : 0;
    };

    // Greedy construction
    for (int pos = 0; pos < n; pos++) {
        int fac = facilities[pos];

        iterId++;
        vector<int> cand;
        cand.reserve(L + R);

        for (int t = 0; t < n && (int)cand.size() < L; t++) {
            int loc = locations[t];
            if (!usedLoc[loc]) {
                cand.push_back(loc);
                mark[loc] = iterId;
            }
        }

        int tries = 0;
        while ((int)cand.size() < L + R && tries < 10 * (L + R)) {
            tries++;
            int loc = rng.nextInt(n);
            if (usedLoc[loc]) continue;
            if (mark[loc] == iterId) continue;
            cand.push_back(loc);
            mark[loc] = iterId;
        }

        if (cand.empty()) {
            for (int loc = 0; loc < n; loc++) if (!usedLoc[loc]) { cand.push_back(loc); break; }
        }

        int bestLoc = cand[0];
        int bestCost = INT_MAX;

        const uint64_t* fR = Frow.row(fac);
        const uint64_t* fC = Fcol.row(fac);

        for (int loc : cand) {
            int c1 = popcount_and(fR, RowProj.row(loc), B);
            int c2 = popcount_and(fC, ColProj.row(loc), B);
            int cost = c1 + c2;
            if (cost < bestCost || (cost == bestCost && distDeg[loc] < distDeg[bestLoc])) {
                bestCost = cost;
                bestLoc = loc;
            }
        }

        // Assign
        int loc = bestLoc;
        locOfFac[fac] = loc;
        facAtLoc[loc] = fac;
        usedLoc[loc] = 1;

        int fw = widx[fac];
        uint64_t fm = bmask[fac];

        // Update RowProj: for each location w, set bit for fac if D[w][loc] == 1
        int colWord = widx[loc];
        uint64_t colMask = bmask[loc];
        for (int w = 0; w < n; w++) {
            const uint64_t* Dw = D.row(w);
            if (Dw[colWord] & colMask) {
                RowProj.row(w)[fw] |= fm;
            }
        }

        // Update ColProj: for each location w, set bit for fac if D[loc][w] == 1
        const uint64_t* Dloc = D.row(loc);
        for (int w = 0; w < n; w++) {
            if (Dloc[widx[w]] & bmask[w]) {
                ColProj.row(w)[fw] |= fm;
            }
        }
    }

    // Local improvement via random swaps
    auto start = chrono::steady_clock::now();
    const double TL = 1.85; // seconds budget for whole program; break early

    int topK = min(n, 500);
    int attempts = 0, accepted = 0;
    int maxAccepted = 400;

    while (accepted < maxAccepted) {
        attempts++;
        if ((attempts & 1023) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (elapsed > TL) break;
        }

        int a = facilities[rng.nextInt(topK)];
        int b = facilities[rng.nextInt(topK)];
        if (a == b) continue;

        int u = locOfFac[a];
        int v = locOfFac[b];
        if (u == v) continue;

        const uint64_t* Ru = RowProj.row(u);
        const uint64_t* Rv = RowProj.row(v);
        const uint64_t* Cu = ColProj.row(u);
        const uint64_t* Cv = ColProj.row(v);

        const uint64_t* FaR = Frow.row(a);
        const uint64_t* FbR = Frow.row(b);
        const uint64_t* FaC = Fcol.row(a);
        const uint64_t* FbC = Fcol.row(b);

        int oa_u = popcount_and(FaR, Ru, B);
        int oa_v = popcount_and(FaR, Rv, B);
        int ob_u = popcount_and(FbR, Ru, B);
        int ob_v = popcount_and(FbR, Rv, B);

        int ia_u = popcount_and(FaC, Cu, B);
        int ia_v = popcount_and(FaC, Cv, B);
        int ib_u = popcount_and(FbC, Cu, B);
        int ib_v = popcount_and(FbC, Cv, B);

        int Faa = getF(a, a);
        int Fab = getF(a, b);
        int Fba = getF(b, a);
        int Fbb = getF(b, b);

        int Duu = getD(u, u);
        int Duv = getD(u, v);
        int Dvu = getD(v, u);
        int Dvv = getD(v, v);

        int out_old = oa_u + ob_v;

        int out_new_a = oa_v + Faa * (Dvv - Dvu) + Fab * (Dvu - Dvv);
        int out_new_b = ob_u + Fba * (Duv - Duu) + Fbb * (Duu - Duv);
        int out_new = out_new_a + out_new_b;

        int in_old_a_excl = ia_u - Faa * Duu - Fba * Dvu;
        int in_new_a_excl = ia_v - Faa * Duv - Fba * Dvv;

        int in_old_b_excl = ib_v - Fab * Duv - Fbb * Dvv;
        int in_new_b_excl = ib_u - Fab * Duu - Fbb * Dvu;

        int in_old = in_old_a_excl + in_old_b_excl;
        int in_new = in_new_a_excl + in_new_b_excl;

        int delta = (out_new + in_new) - (out_old + in_old);
        if (delta >= 0) continue;

        // Apply swap
        locOfFac[a] = v;
        locOfFac[b] = u;
        facAtLoc[u] = b;
        facAtLoc[v] = a;

        // Update RowProj bits for a and b across all locations w
        int aw = widx[a], bw = widx[b];
        uint64_t am = bmask[a], bm = bmask[b];
        int uW = widx[u], vW = widx[v];
        uint64_t uM = bmask[u], vM = bmask[v];

        for (int w = 0; w < n; w++) {
            const uint64_t* Dw = D.row(w);
            int valA = (Dw[vW] & vM) ? 1 : 0; // D[w][v]
            int valB = (Dw[uW] & uM) ? 1 : 0; // D[w][u]
            uint64_t* Rw = RowProj.row(w);
            if (valA) Rw[aw] |= am; else Rw[aw] &= ~am;
            if (valB) Rw[bw] |= bm; else Rw[bw] &= ~bm;
        }

        // Update ColProj bits for a and b across all locations w
        const uint64_t* Dv = D.row(v);
        const uint64_t* Du = D.row(u);
        for (int w = 0; w < n; w++) {
            int valA = (Dv[widx[w]] & bmask[w]) ? 1 : 0; // D[v][w]
            int valB = (Du[widx[w]] & bmask[w]) ? 1 : 0; // D[u][w]
            uint64_t* Cw = ColProj.row(w);
            if (valA) Cw[aw] |= am; else Cw[aw] &= ~am;
            if (valB) Cw[bw] |= bm; else Cw[bw] &= ~bm;
        }

        accepted++;
    }

    // Output permutation: p_i = location assigned to facility i (1-indexed)
    string out;
    out.reserve((size_t)n * 6);
    for (int i = 0; i < n; i++) {
        int v = locOfFac[i] + 1;
        char buf[32];
        auto [ptr, ec] = to_chars(buf, buf + 32, v);
        out.append(buf, ptr);
        out.push_back(i + 1 == n ? '\n' : ' ');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}