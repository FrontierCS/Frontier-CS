#include <bits/stdc++.h>
using namespace std;

static constexpr int MAXN = 20;
static constexpr int LMIN = 2;
static constexpr int LMAX = 12;

static constexpr int FMIN = 4;
static constexpr int FMAX = 10;

struct XorShift64 {
    uint64_t x;
    explicit XorShift64(uint64_t seed = 88172645463325252ull) : x(seed) {}
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int n) { return (int)(nextU64() % (uint64_t)n); }
    double nextDouble() { return (nextU64() >> 11) * (1.0 / 9007199254740992.0); } // [0,1)
};

struct SmallSet {
    array<uint64_t, MAXN> v{};
    uint8_t sz = 0;
};

struct LineData {
    array<SmallSet, LMAX + 1> codes;
};

static inline bool containsCode(const SmallSet& s, uint64_t x) {
    const uint64_t* b = s.v.data();
    const uint64_t* e = b + s.sz;
    return std::binary_search(b, e, x);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    cin >> N >> M;

    vector<int> slen(M);
    vector<uint64_t> scode(M);

    vector<string> sraw(M);
    for (int i = 0; i < M; i++) {
        cin >> sraw[i];
        slen[i] = (int)sraw[i].size();
        uint64_t code = 0;
        for (char ch : sraw[i]) {
            int v = ch - 'A';
            code = code * 8 + (uint64_t)v;
        }
        scode[i] = code;
    }

    array<uint64_t, LMAX + 1> pow8{};
    pow8[0] = 1;
    for (int i = 1; i <= LMAX; i++) pow8[i] = pow8[i - 1] * 8ULL;

    array<int, LMAX + 1> wlen{};
    for (int L = 0; L <= LMAX; L++) wlen[L] = 0;
    for (int L = FMIN; L <= FMAX; L++) wlen[L] = 1 << (L - FMIN);

    array<unordered_map<uint64_t, int>, LMAX + 1> freq;
    for (int L = 0; L <= LMAX; L++) {
        freq[L].reserve(4096);
        freq[L].max_load_factor(0.7f);
    }
    for (int i = 0; i < M; i++) {
        const string& s = sraw[i];
        int Ls = (int)s.size();
        vector<int> a(Ls);
        for (int j = 0; j < Ls; j++) a[j] = s[j] - 'A';

        for (int L = FMIN; L <= FMAX && L <= Ls; L++) {
            int w = wlen[L];
            for (int st = 0; st + L <= Ls; st++) {
                uint64_t code = 0;
                for (int p = 0; p < L; p++) code = code * 8 + (uint64_t)a[st + p];
                freq[L][code] += w;
            }
        }
    }

    auto buildLineDataAndFreq = [&](const array<uint8_t, MAXN>& arr) -> pair<LineData, int> {
        LineData ld;
        int lineFreq = 0;

        array<uint8_t, MAXN * 2> dbl{};
        for (int i = 0; i < 2 * N; i++) dbl[i] = arr[i % N];

        array<uint64_t, MAXN> tmp{};

        for (int L = LMIN; L <= LMAX; L++) {
            uint64_t pow = pow8[L - 1];
            uint64_t code = 0;
            for (int p = 0; p < L; p++) code = code * 8 + (uint64_t)dbl[p];
            tmp[0] = code;
            for (int st = 1; st < N; st++) {
                code = (code - (uint64_t)dbl[st - 1] * pow) * 8 + (uint64_t)dbl[st + L - 1];
                tmp[st] = code;
            }

            if (L >= FMIN && L <= FMAX) {
                auto& mp = freq[L];
                for (int st = 0; st < N; st++) {
                    auto it = mp.find(tmp[st]);
                    if (it != mp.end()) lineFreq += it->second;
                }
            }

            sort(tmp.begin(), tmp.begin() + N);
            SmallSet ss;
            ss.sz = 0;
            for (int i = 0; i < N; i++) {
                if (i == 0 || tmp[i] != tmp[i - 1]) {
                    ss.v[ss.sz++] = tmp[i];
                }
            }
            ld.codes[L] = ss;
        }

        return {ld, lineFreq};
    };

    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    XorShift64 rng(seed ^ (uint64_t)(uintptr_t)&seed);

    array<array<uint8_t, MAXN>, MAXN> mat{};
    for (int i = 0; i < N; i++) for (int j = 0; j < N; j++) mat[i][j] = (uint8_t)rng.nextInt(8);

    int LINES = 2 * N;
    vector<LineData> lines(LINES);
    vector<int> lineFreq(LINES, 0);

    auto rebuildAllLines = [&]() {
        for (int r = 0; r < N; r++) {
            array<uint8_t, MAXN> arr{};
            for (int j = 0; j < N; j++) arr[j] = mat[r][j];
            auto [ld, lf] = buildLineDataAndFreq(arr);
            lines[r] = ld;
            lineFreq[r] = lf;
        }
        for (int c = 0; c < N; c++) {
            array<uint8_t, MAXN> arr{};
            for (int i = 0; i < N; i++) arr[i] = mat[i][c];
            auto [ld, lf] = buildLineDataAndFreq(arr);
            lines[N + c] = ld;
            lineFreq[N + c] = lf;
        }
    };

    rebuildAllLines();

    vector<uint64_t> mask(M, 0), maskCand(M, 0);
    auto computeMasksAndSatisfied = [&]() -> int {
        int sat = 0;
        for (int i = 0; i < M; i++) {
            uint64_t m = 0;
            int L = slen[i];
            uint64_t code = scode[i];
            for (int li = 0; li < LINES; li++) {
                if (containsCode(lines[li].codes[L], code)) m |= (1ULL << li);
            }
            mask[i] = m;
            if (m) sat++;
        }
        return sat;
    };

    int satisfied = computeMasksAndSatisfied();
    long long freqTotal = 0;
    for (int li = 0; li < LINES; li++) freqTotal += lineFreq[li];

    const long long WFULL = 10000;

    auto evalChange = [&](int r, int c, uint8_t newCh,
                          LineData& newRow, int& newRowFreq,
                          LineData& newCol, int& newColFreq,
                          int& deltaSat, long long& deltaFreq,
                          long long& deltaScore) {
        int lrow = r;
        int lcol = N + c;

        array<uint8_t, MAXN> rowArr{};
        for (int j = 0; j < N; j++) rowArr[j] = (j == c ? newCh : mat[r][j]);
        array<uint8_t, MAXN> colArr{};
        for (int i = 0; i < N; i++) colArr[i] = (i == r ? newCh : mat[i][c]);

        auto pr = buildLineDataAndFreq(rowArr);
        newRow = pr.first;
        newRowFreq = pr.second;

        auto pc = buildLineDataAndFreq(colArr);
        newCol = pc.first;
        newColFreq = pc.second;

        deltaSat = 0;
        uint64_t bitRow = 1ULL << lrow;
        uint64_t bitCol = 1ULL << lcol;

        for (int i = 0; i < M; i++) {
            uint64_t oldm = mask[i];
            bool oldSat = (oldm != 0);
            uint64_t m = oldm;

            int L = slen[i];
            uint64_t code = scode[i];

            bool inRow = containsCode(newRow.codes[L], code);
            bool inCol = containsCode(newCol.codes[L], code);

            if (inRow) m |= bitRow;
            else m &= ~bitRow;

            if (inCol) m |= bitCol;
            else m &= ~bitCol;

            maskCand[i] = m;
            bool newSat = (m != 0);
            deltaSat += (int)newSat - (int)oldSat;
        }

        deltaFreq = (long long)(newRowFreq - lineFreq[lrow]) + (long long)(newColFreq - lineFreq[lcol]);
        deltaScore = WFULL * (long long)deltaSat + deltaFreq;
    };

    auto applyChange = [&](int r, int c, uint8_t newCh,
                           const LineData& newRow, int newRowFreq,
                           const LineData& newCol, int newColFreq,
                           int deltaSat, long long deltaFreq) {
        int lrow = r;
        int lcol = N + c;

        mat[r][c] = newCh;
        lines[lrow] = newRow;
        lines[lcol] = newCol;

        freqTotal += deltaFreq;
        lineFreq[lrow] = newRowFreq;
        lineFreq[lcol] = newColFreq;

        satisfied += deltaSat;
        mask.swap(maskCand);
    };

    array<array<uint8_t, MAXN>, MAXN> bestMat = mat;
    int bestSatisfied = satisfied;
    long long bestFreq = freqTotal;

    // One greedy pass (small)
    {
        vector<int> pos(N * N);
        iota(pos.begin(), pos.end(), 0);
        shuffle(pos.begin(), pos.end(), std::mt19937((uint32_t)rng.nextU32()));

        for (int idx : pos) {
            int r = idx / N;
            int c = idx % N;
            uint8_t oldCh = mat[r][c];

            long long bestDeltaScore = 0;
            uint8_t bestCh = oldCh;

            for (uint8_t ch = 0; ch < 8; ch++) {
                if (ch == oldCh) continue;
                LineData newRow, newCol;
                int newRowFreq, newColFreq;
                int deltaSat;
                long long deltaFreq, deltaScore;
                evalChange(r, c, ch, newRow, newRowFreq, newCol, newColFreq, deltaSat, deltaFreq, deltaScore);
                if (deltaScore > bestDeltaScore) {
                    bestDeltaScore = deltaScore;
                    bestCh = ch;
                }
            }
            if (bestCh != oldCh && bestDeltaScore > 0) {
                LineData newRow, newCol;
                int newRowFreq, newColFreq;
                int deltaSat;
                long long deltaFreq, deltaScore;
                evalChange(r, c, bestCh, newRow, newRowFreq, newCol, newColFreq, deltaSat, deltaFreq, deltaScore);
                applyChange(r, c, bestCh, newRow, newRowFreq, newCol, newColFreq, deltaSat, deltaFreq);

                if (satisfied > bestSatisfied || (satisfied == bestSatisfied && freqTotal > bestFreq)) {
                    bestSatisfied = satisfied;
                    bestFreq = freqTotal;
                    bestMat = mat;
                }
            }
        }
    }

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85;
    const double T0 = 20000.0;
    const double T1 = 100.0;

    long long iters = 0;
    while (true) {
        iters++;
        if ((iters & 1023) == 0) {
            double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
            if (elapsed > TIME_LIMIT) break;
        }

        int r = rng.nextInt(N);
        int c = rng.nextInt(N);
        uint8_t oldCh = mat[r][c];
        uint8_t newCh = (uint8_t)rng.nextInt(8);
        if (newCh == oldCh) continue;

        LineData newRow, newCol;
        int newRowFreq, newColFreq;
        int deltaSat;
        long long deltaFreq, deltaScore;
        evalChange(r, c, newCh, newRow, newRowFreq, newCol, newColFreq, deltaSat, deltaFreq, deltaScore);

        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        double t = min(1.0, elapsed / TIME_LIMIT);
        double temp = T0 * (1.0 - t) + T1 * t;

        bool accept = false;
        if (deltaScore >= 0) {
            accept = true;
        } else {
            double x = (double)deltaScore / temp;
            if (x > -60.0) {
                double p = exp(x);
                if (rng.nextDouble() < p) accept = true;
            }
        }

        if (accept) {
            applyChange(r, c, newCh, newRow, newRowFreq, newCol, newColFreq, deltaSat, deltaFreq);
            if (satisfied > bestSatisfied || (satisfied == bestSatisfied && freqTotal > bestFreq)) {
                bestSatisfied = satisfied;
                bestFreq = freqTotal;
                bestMat = mat;
                if (bestSatisfied == M) break;
            }
        }
    }

    static const char ALPH[8] = {'A','B','C','D','E','F','G','H'};
    for (int i = 0; i < N; i++) {
        string out;
        out.resize(N);
        for (int j = 0; j < N; j++) out[j] = ALPH[bestMat[i][j]];
        cout << out << "\n";
    }
    return 0;
}