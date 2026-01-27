#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static const size_t BUFSIZE = 1<<20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner(): idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    inline bool skipBlanks() {
        char c;
        do {
            c = getChar();
            if (!c) return false;
        } while (c <= ' ');
        idx--;
        return true;
    }
    inline bool readInt(int &out) {
        if (!skipBlanks()) return false;
        char c = getChar();
        bool neg = false;
        if (c=='-') { neg = true; c = getChar(); }
        int x = 0;
        while (c > ' ') {
            x = x*10 + (c - '0');
            c = getChar();
        }
        out = neg ? -x : x;
        return true;
    }
};

static inline long long swapDelta(
    int n,
    const unsigned char* D, const unsigned char* DT,
    const unsigned char* F, const unsigned char* FT,
    const int* p,
    int a, int b
) {
    int A = p[a];
    int B = p[b];
    if (A == B) return 0;

    const unsigned char* DrowA = D + (size_t)A * n;
    const unsigned char* DrowB = D + (size_t)B * n;
    const unsigned char* DTrowA = DT + (size_t)A * n;
    const unsigned char* DTrowB = DT + (size_t)B * n;

    const unsigned char* FrowA = F + (size_t)a * n;
    const unsigned char* FrowB = F + (size_t)b * n;
    const unsigned char* FTrowA = FT + (size_t)a * n; // F[k][a] across k
    const unsigned char* FTrowB = FT + (size_t)b * n; // F[k][b] across k

    long long delta = 0;

    for (int k = 0; k < n; ++k) {
        if (k == a || k == b) continue;
        int pk = p[k];
        int dBA = (int)DrowB[pk] - (int)DrowA[pk];
        int dTBTA = (int)DTrowB[pk] - (int)DTrowA[pk];

        delta += (int)FrowA[k] * dBA;
        delta -= (int)FrowB[k] * dBA;

        delta += (int)FTrowA[k] * dTBTA;
        delta -= (int)FTrowB[k] * dTBTA;
    }

    // Terms involving a and b directly
    int FAA = (int)FrowA[a];
    int FBB = (int)FrowB[b];
    int FAB = (int)FrowA[b];
    int FBA = (int)FrowB[a];

    int DAA = (int)DrowA[A];
    int DBB = (int)DrowB[B];
    int DBA = (int)DrowB[A];
    int DAB = (int)DrowA[B];

    delta += FAA * (DBB - DAA);
    delta += FBB * (DAA - DBB);
    delta += FAB * (DBA - DAB);
    delta += FBA * (DAB - DBA);

    return delta;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    auto t_start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.80; // seconds

    FastScanner in;
    int n;
    if (!in.readInt(n)) return 0;

    size_t N2 = (size_t)n * (size_t)n;
    vector<unsigned char> D(N2), DT(N2), F(N2), FT(N2);
    vector<int> degDOut(n,0), degDIn(n,0), degFOut(n,0), degFIn(n,0);

    // Read D and build its transpose
    for (int i = 0; i < n; ++i) {
        size_t base = (size_t)i * n;
        for (int j = 0; j < n; ++j) {
            int v; in.readInt(v);
            unsigned char val = (unsigned char)v;
            D[base + j] = val;
            DT[(size_t)j * n + i] = val;
            if (val) { degDOut[i]++; degDIn[j]++; }
        }
    }

    // Read F and build its transpose
    for (int i = 0; i < n; ++i) {
        size_t base = (size_t)i * n;
        for (int j = 0; j < n; ++j) {
            int v; in.readInt(v);
            unsigned char val = (unsigned char)v;
            F[base + j] = val;
            FT[(size_t)j * n + i] = val;
            if (val) { degFOut[i]++; degFIn[j]++; }
        }
    }

    // Initial assignment: sort facilities by (degFOut+degFIn) desc, locations by (degDOut+degDIn) asc
    vector<int> facOrder(n), locOrder(n);
    iota(facOrder.begin(), facOrder.end(), 0);
    iota(locOrder.begin(), locOrder.end(), 0);

    vector<int> scoreF(n), scoreD(n);
    for (int i = 0; i < n; ++i) {
        scoreF[i] = degFOut[i] + degFIn[i];
        scoreD[i] = degDOut[i] + degDIn[i];
    }

    sort(facOrder.begin(), facOrder.end(), [&](int a, int b){
        if (scoreF[a] != scoreF[b]) return scoreF[a] > scoreF[b];
        if (degFOut[a] != degFOut[b]) return degFOut[a] > degFOut[b];
        if (degFIn[a] != degFIn[b]) return degFIn[a] > degFIn[b];
        return a < b;
    });
    sort(locOrder.begin(), locOrder.end(), [&](int a, int b){
        if (scoreD[a] != scoreD[b]) return scoreD[a] < scoreD[b];
        if (degDOut[a] != degDOut[b]) return degDOut[a] < degDOut[b];
        if (degDIn[a] != degDIn[b]) return degDIn[a] < degDIn[b];
        return a < b;
    });

    vector<int> p(n, -1), posOfLoc(n, -1);
    for (int i = 0; i < n; ++i) {
        int fac = facOrder[i];
        int loc = locOrder[i];
        p[fac] = loc;
        posOfLoc[loc] = fac;
    }

    // Ranks and badness
    vector<int> facRank(n), locRank(n);
    for (int idx = 0; idx < n; ++idx) {
        facRank[facOrder[idx]] = idx;
        locRank[locOrder[idx]] = idx;
    }

    auto elapsed_sec = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - t_start).count();
    };

    auto improve_round = [&](double time_budget_sec) {
        vector<int> bad(n);
        for (int i = 0; i < n; ++i) {
            bad[i] = abs(facRank[i] - locRank[p[i]]);
        }
        vector<int> idxs(n);
        iota(idxs.begin(), idxs.end(), 0);
        sort(idxs.begin(), idxs.end(), [&](int a, int b){
            if (bad[a] != bad[b]) return bad[a] > bad[b];
            return a < b;
        });

        int M = min(n, max(10, n / 4)); // consider top quarter at most
        int T = max(1, n / 80);         // neighbor window ~1.25% of n
        if (n <= 200) { M = n; T = max(1, n/20); }
        else if (n <= 600) { M = min(n, 300); T = max(2, n/40); }
        else if (n <= 1200) { M = min(n, 300); T = max(2, n/60); }
        else { M = min(n, 350); T = max(2, n/80); }

        bool improved = false;

        for (int iter = 0; iter < M; ++iter) {
            if (elapsed_sec() >= time_budget_sec) break;
            int a = idxs[iter];
            int r = facRank[a];

            // Try candidates around rank r in increasing distance
            for (int offset = 0; offset <= T; ++offset) {
                if (elapsed_sec() >= time_budget_sec) break;
                // Two sides: r-offset and r+offset
                int js[2] = {r - offset, r + offset};
                for (int side = 0; side < 2; ++side) {
                    int j = js[side];
                    if (j < 0 || j >= n) continue;
                    int locCand = locOrder[j];
                    int b = posOfLoc[locCand];
                    if (a == b) continue;

                    long long d = swapDelta(n, D.data(), DT.data(), F.data(), FT.data(), p.data(), a, b);
                    if (d < 0) {
                        // Apply swap
                        int A = p[a], B = p[b];
                        p[a] = B; p[b] = A;
                        posOfLoc[A] = b;
                        posOfLoc[B] = a;
                        // Update badness for a and b
                        bad[a] = abs(facRank[a] - locRank[p[a]]);
                        bad[b] = abs(facRank[b] - locRank[p[b]]);
                        improved = true;
                        goto next_a; // move to next 'a'
                    }
                }
            }
            next_a:;
        }

        return improved;
    };

    double deadline = TIME_LIMIT;
    // One or two targeted improvement rounds within time budget
    bool any = false;
    if (elapsed_sec() < deadline) any = improve_round(deadline);
    if (any && elapsed_sec() < deadline) improve_round(deadline);

    // A few random pair improvements within remaining time
    uint64_t rng = chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rng_next = [&]() -> uint32_t {
        rng ^= rng >> 12; rng ^= rng << 25; rng ^= rng >> 27;
        return (uint32_t)((rng * 0x2545F4914F6CDD1DULL) >> 32);
    };

    int attempts = max(100, min(4000, (int)(2e7 / max(1, n)))); // approx ops budget
    for (int t = 0; t < attempts && elapsed_sec() < deadline; ++t) {
        int a = (int)(rng_next() % n);
        int b = (int)(rng_next() % n);
        if (a == b) continue;
        long long d = swapDelta(n, D.data(), DT.data(), F.data(), FT.data(), p.data(), a, b);
        if (d < 0) {
            int A = p[a], B = p[b];
            p[a] = B; p[b] = A;
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