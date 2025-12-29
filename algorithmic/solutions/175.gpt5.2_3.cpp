#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    size_t idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        char c = readChar();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = readChar();
            if (!c) return false;
        }
        T sign = 1;
        if (c == '-') {
            sign = -1;
            c = readChar();
        }
        T val = 0;
        while (c >= '0' && c <= '9') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = val * sign;
        return true;
    }
};

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    inline uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    int m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<uint16_t> va(m), vb(m), vc(m);
    vector<uint8_t> na(m), nb(m), nc(m);

    vector<int> cnt(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int a, b, c;
        fs.readInt(a); fs.readInt(b); fs.readInt(c);

        int av = a < 0 ? -a : a;
        int bv = b < 0 ? -b : b;
        int cv = c < 0 ? -c : c;

        va[i] = (uint16_t)av; vb[i] = (uint16_t)bv; vc[i] = (uint16_t)cv;
        na[i] = (uint8_t)(a < 0); nb[i] = (uint8_t)(b < 0); nc[i] = (uint8_t)(c < 0);

        cnt[av]++; cnt[bv]++; cnt[cv]++;
    }

    vector<int> start(n + 2, 0);
    start[1] = 0;
    for (int v = 1; v <= n; v++) start[v + 1] = start[v] + cnt[v];
    int totalOcc = start[n + 1];
    vector<int> occ(totalOcc);
    vector<int> ptr = start;

    for (int i = 0; i < m; i++) {
        occ[ptr[va[i]]++] = i;
        occ[ptr[vb[i]]++] = i;
        occ[ptr[vc[i]]++] = i;
    }

    vector<int> occSize(n + 1, 0);
    int maxOcc = 0;
    for (int v = 1; v <= n; v++) {
        occSize[v] = start[v + 1] - start[v];
        maxOcc = max(maxOcc, occSize[v]);
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    SplitMix64 rng(seed);

    auto evalSat = [&](const uint8_t* val) -> long long {
        long long sat = 0;
        for (int i = 0; i < m; i++) {
            int a = (val[va[i]] ^ na[i]);
            int b = (val[vb[i]] ^ nb[i]);
            int c = (val[vc[i]] ^ nc[i]);
            sat += (a | b | c) ? 1 : 0;
        }
        return sat;
    };

    vector<uint8_t> bestVal(n + 1, 0);
    long long bestSat = -1;

    int K;
    if (m == 0) K = 1;
    else if (m > 1000000) K = 3;
    else if (m > 300000) K = 5;
    else K = 8;

    vector<uint8_t> val(n + 1, 0);
    for (int t = 0; t < K; t++) {
        for (int v = 1; v <= n; v++) val[v] = (uint8_t)(rng.nextU64() & 1ULL);
        long long sat = evalSat(val.data());
        if (sat > bestSat) {
            bestSat = sat;
            bestVal = val;
        }
    }

    if (m == 0) {
        string out;
        out.reserve((size_t)n * 2 + 1);
        for (int i = 1; i <= n; i++) {
            out.push_back(bestVal[i] ? '1' : '0');
            out.push_back(i == n ? '\n' : ' ');
        }
        fwrite(out.data(), 1, out.size(), stdout);
        return 0;
    }

    val = bestVal;

    vector<uint8_t> trueCount(m, 0);
    vector<int> posUnsat(m, -1);
    vector<int> unsat;
    unsat.reserve((size_t)m / 8 + 1);

    long long satCount = 0;
    for (int i = 0; i < m; i++) {
        int a = (val[va[i]] ^ na[i]);
        int b = (val[vb[i]] ^ nb[i]);
        int c = (val[vc[i]] ^ nc[i]);
        uint8_t cntt = (uint8_t)(a + b + c);
        trueCount[i] = cntt;
        if (cntt == 0) {
            posUnsat[i] = (int)unsat.size();
            unsat.push_back(i);
        } else {
            satCount++;
        }
    }

    vector<uint32_t> seenStamp(m, 0);
    uint32_t stampCounter = 1;

    auto addUnsat = [&](int cl) {
        if (posUnsat[cl] != -1) return;
        posUnsat[cl] = (int)unsat.size();
        unsat.push_back(cl);
    };
    auto removeUnsat = [&](int cl) {
        int p = posUnsat[cl];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posUnsat[last] = p;
        unsat.pop_back();
        posUnsat[cl] = -1;
    };

    auto clauseCountNow = [&](int i) -> uint8_t {
        int a = (val[va[i]] ^ na[i]);
        int b = (val[vb[i]] ^ nb[i]);
        int c = (val[vc[i]] ^ nc[i]);
        return (uint8_t)(a + b + c);
    };

    auto clauseSatAfterFlip = [&](int i, int var, uint8_t newVal) -> bool {
        uint8_t xa = (va[i] == var ? newVal : val[va[i]]);
        uint8_t xb = (vb[i] == var ? newVal : val[vb[i]]);
        uint8_t xc = (vc[i] == var ? newVal : val[vc[i]]);
        int a = (xa ^ na[i]);
        int b = (xb ^ nb[i]);
        int c = (xc ^ nc[i]);
        return (a | b | c) != 0;
    };

    auto clauseCountAfterFlip = [&](int i, int var, uint8_t newVal) -> uint8_t {
        uint8_t xa = (va[i] == var ? newVal : val[va[i]]);
        uint8_t xb = (vb[i] == var ? newVal : val[vb[i]]);
        uint8_t xc = (vc[i] == var ? newVal : val[vc[i]]);
        int a = (xa ^ na[i]);
        int b = (xb ^ nb[i]);
        int c = (xc ^ nc[i]);
        return (uint8_t)(a + b + c);
    };

    vector<uint8_t> bestOverallVal = val;
    long long bestOverallSat = satCount;

    // Greedy improving pass: flip variable if it increases satisfied clauses
    for (int v = 1; v <= n; v++) {
        if (occSize[v] == 0) continue;
        uint8_t newVal = (uint8_t)(val[v] ^ 1);
        int delta = 0;

        uint32_t stamp = ++stampCounter;
        for (int p = start[v]; p < start[v + 1]; p++) {
            int cl = occ[p];
            if (seenStamp[cl] == stamp) continue;
            seenStamp[cl] = stamp;

            bool oldSat = (trueCount[cl] != 0);
            bool newSat = clauseSatAfterFlip(cl, v, newVal);
            delta += (int)newSat - (int)oldSat;
        }

        if (delta > 0) {
            val[v] = newVal;
            uint32_t stamp2 = ++stampCounter;
            for (int p = start[v]; p < start[v + 1]; p++) {
                int cl = occ[p];
                if (seenStamp[cl] == stamp2) continue;
                seenStamp[cl] = stamp2;

                uint8_t oldCnt = trueCount[cl];
                uint8_t newCnt = clauseCountNow(cl);

                if (oldCnt == 0 && newCnt > 0) {
                    if (posUnsat[cl] != -1) { removeUnsat(cl); satCount++; }
                } else if (oldCnt > 0 && newCnt == 0) {
                    if (posUnsat[cl] == -1) { addUnsat(cl); satCount--; }
                }
                trueCount[cl] = newCnt;
            }

            if (satCount > bestOverallSat) {
                bestOverallSat = satCount;
                bestOverallVal = val;
            }
            if (unsat.empty()) break;
        }
    }

    auto breakCountEst = [&](int var) -> int {
        int occN = occSize[var];
        if (occN == 0) return 0;
        uint8_t newVal = (uint8_t)(val[var] ^ 1);

        constexpr int FULL_LIMIT = 30000;
        constexpr int SAMPLE = 4000;

        if (occN <= FULL_LIMIT) {
            int bc = 0;
            uint32_t stamp = ++stampCounter;
            for (int p = start[var]; p < start[var + 1]; p++) {
                int cl = occ[p];
                if (seenStamp[cl] == stamp) continue;
                seenStamp[cl] = stamp;

                if (trueCount[cl] == 0) continue;
                if (clauseCountAfterFlip(cl, var, newVal) == 0) bc++;
            }
            return bc;
        } else {
            int samp = min(SAMPLE, occN);
            int bc = 0;
            for (int t = 0; t < samp; t++) {
                int p = start[var] + (int)(rng.nextU32() % (uint32_t)occN);
                int cl = occ[p];
                if (trueCount[cl] == 0) continue;
                if (clauseCountAfterFlip(cl, var, newVal) == 0) bc++;
            }
            long long est = (long long)bc * occN / max(1, samp);
            if (est > INT_MAX) est = INT_MAX;
            return (int)est;
        }
    };

    int steps;
    if (m > 1000000) steps = 3500;
    else steps = 7000;
    if (maxOcc > 200000) steps = min(steps, 1500);

    for (int step = 0; step < steps; step++) {
        if (unsat.empty()) break;

        if (satCount > bestOverallSat) {
            bestOverallSat = satCount;
            bestOverallVal = val;
        }

        int cl = unsat[(size_t)(rng.nextU32() % (uint32_t)unsat.size())];

        int vars[3];
        int k = 0;
        uint16_t vv[3] = {va[cl], vb[cl], vc[cl]};
        for (int i = 0; i < 3; i++) {
            int v = (int)vv[i];
            bool ok = true;
            for (int j = 0; j < k; j++) if (vars[j] == v) { ok = false; break; }
            if (ok) vars[k++] = v;
        }

        int chosenVar;
        if ((rng.nextU32() % 100) < 30) {
            chosenVar = vars[rng.nextU32() % (uint32_t)k];
        } else {
            int bestB = INT_MAX;
            chosenVar = vars[0];
            for (int i = 0; i < k; i++) {
                int v = vars[i];
                int bc = breakCountEst(v);
                if (bc < bestB || (bc == bestB && (rng.nextU32() & 1U))) {
                    bestB = bc;
                    chosenVar = v;
                    if (bestB == 0) break;
                }
            }
        }

        val[chosenVar] ^= 1;

        uint32_t stamp = ++stampCounter;
        for (int p = start[chosenVar]; p < start[chosenVar + 1]; p++) {
            int cc = occ[p];
            if (seenStamp[cc] == stamp) continue;
            seenStamp[cc] = stamp;

            uint8_t oldCnt = trueCount[cc];
            uint8_t newCnt = clauseCountNow(cc);

            if (oldCnt == 0 && newCnt > 0) {
                if (posUnsat[cc] != -1) { removeUnsat(cc); satCount++; }
            } else if (oldCnt > 0 && newCnt == 0) {
                if (posUnsat[cc] == -1) { addUnsat(cc); satCount--; }
            }
            trueCount[cc] = newCnt;
        }
    }

    if (satCount > bestOverallSat) {
        bestOverallSat = satCount;
        bestOverallVal = val;
    }

    string out;
    out.reserve((size_t)n * 2 + 1);
    for (int i = 1; i <= n; i++) {
        out.push_back(bestOverallVal[i] ? '1' : '0');
        out.push_back(i == n ? '\n' : ' ');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}