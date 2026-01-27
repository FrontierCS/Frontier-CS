#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
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

    inline int nextInt() {
        char c;
        do c = readChar(); while (c && c <= ' ');
        int sgn = 1;
        if (c == '-') { sgn = -1; c = readChar(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
        }
        return x * sgn;
    }

    inline int nextBit() {
        char c = readChar();
        while (c && (c == ' ' || c == '\n' || c == '\r' || c == '\t' || c == '\v' || c == '\f')) c = readChar();
        while (c && c != '0' && c != '1') c = readChar();
        return c == '1';
    }
};

static inline int getBitRow(const uint64_t* row, int c) {
    return (int)((row[c >> 6] >> (c & 63)) & 1ULL);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n = fs.nextInt();
    int m = (n + 63) >> 6;

    vector<uint64_t> D((size_t)n * m, 0ULL), F((size_t)n * m, 0ULL);
    vector<int> distRow(n, 0), distCol(n, 0), flowRow(n, 0), flowCol(n, 0);

    auto setBit = [&](vector<uint64_t>& M, int r, int c) {
        M[(size_t)r * m + (c >> 6)] |= (1ULL << (c & 63));
    };

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x = fs.nextBit();
            if (x) {
                setBit(D, i, j);
                distRow[i]++; distCol[j]++;
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x = fs.nextBit();
            if (x) {
                setBit(F, i, j);
                flowRow[i]++; flowCol[j]++;
            }
        }
    }

    vector<int> facDeg(n), locDeg(n);
    for (int i = 0; i < n; ++i) {
        facDeg[i] = flowRow[i] + flowCol[i];
        locDeg[i] = distRow[i] + distCol[i];
    }

    vector<int> facIdx(n), locIdx(n);
    iota(facIdx.begin(), facIdx.end(), 0);
    iota(locIdx.begin(), locIdx.end(), 0);

    sort(facIdx.begin(), facIdx.end(), [&](int a, int b) {
        if (facDeg[a] != facDeg[b]) return facDeg[a] > facDeg[b];
        return a < b;
    });
    sort(locIdx.begin(), locIdx.end(), [&](int a, int b) {
        if (locDeg[a] != locDeg[b]) return locDeg[a] < locDeg[b];
        return a < b;
    });

    vector<int> p(n, 0);
    for (int t = 0; t < n; ++t) p[facIdx[t]] = locIdx[t];

    uint64_t seed = 88172645463393265ULL ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    auto rng = [&]() -> uint64_t {
        seed ^= seed << 7;
        seed ^= seed >> 9;
        return seed;
    };
    auto rndInt = [&](int bound) -> int {
        return (int)(rng() % (uint64_t)bound);
    };

    auto deltaSwap = [&](int a, int b) -> int {
        if (a == b) return 0;
        int la = p[a], lb = p[b];
        if (la == lb) return 0;

        const uint64_t* FrowA = &F[(size_t)a * m];
        const uint64_t* FrowB = &F[(size_t)b * m];
        const uint64_t* DrowLA = &D[(size_t)la * m];
        const uint64_t* DrowLB = &D[(size_t)lb * m];

        int delta = 0;

        for (int k = 0; k < n; ++k) {
            if (k == a || k == b) continue;
            int lock = p[k];

            int fa_k = getBitRow(FrowA, k);
            int fb_k = getBitRow(FrowB, k);
            if (fa_k || fb_k) {
                int da = getBitRow(DrowLA, lock);
                int db = getBitRow(DrowLB, lock);
                int diff = db - da;
                if (fa_k) delta += diff;
                if (fb_k) delta -= diff;
            }

            const uint64_t* FrowK = &F[(size_t)k * m];
            int fk_a = getBitRow(FrowK, a);
            int fk_b = getBitRow(FrowK, b);
            if (fk_a || fk_b) {
                const uint64_t* DrowLK = &D[(size_t)lock * m];
                int dka = getBitRow(DrowLK, la);
                int dkb = getBitRow(DrowLK, lb);
                int diff2 = dkb - dka;
                if (fk_a) delta += diff2;
                if (fk_b) delta -= diff2;
            }
        }

        int faa = getBitRow(FrowA, a);
        int fab = getBitRow(FrowA, b);
        int fba = getBitRow(FrowB, a);
        int fbb = getBitRow(FrowB, b);
        if (faa || fab || fba || fbb) {
            int daa = getBitRow(DrowLA, la);
            int dbb = getBitRow(DrowLB, lb);
            int dab = getBitRow(DrowLA, lb);
            int dba = getBitRow(DrowLB, la);
            delta += faa * (dbb - daa);
            delta += fab * (dba - dab);
            delta += fba * (dab - dba);
            delta += fbb * (daa - dbb);
        }

        return delta;
    };

    const int K = min(n, 300);
    const int CANDS = 3;
    const int MAX_IT = 20000;
    const double TIME_LIMIT_SEC = 1.0;

    auto t0 = chrono::steady_clock::now();
    for (int it = 0; it < MAX_IT; ++it) {
        if ((it & 255) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
            if (elapsed > TIME_LIMIT_SEC) break;
        }

        int a;
        if (rng() & 1ULL) a = facIdx[rndInt(K)];
        else a = rndInt(n);

        int bestDelta = 0;
        int bestB = -1;

        for (int c = 0; c < CANDS; ++c) {
            int b = rndInt(n);
            if (b == a) continue;
            int d = deltaSwap(a, b);
            if (d < bestDelta) {
                bestDelta = d;
                bestB = b;
            }
        }

        if (bestB != -1) {
            std::swap(p[a], p[bestB]);
        }
    }

    string out;
    out.reserve((size_t)n * 6);
    for (int i = 0; i < n; ++i) {
        int v = p[i] + 1;
        out += to_string(v);
        out += (i + 1 == n) ? '\n' : ' ';
    }
    cout << out;
    return 0;
}