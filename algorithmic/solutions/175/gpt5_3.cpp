#include <bits/stdc++.h>
using namespace std;

// Fast input reader
struct FastScanner {
    static const size_t BUFSIZE = 1 << 20; // 1MB
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }
    template<typename T>
    bool nextInt(T &out) {
        char c;
        T sign = 1;
        T num = 0;
        c = read();
        if (!c) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = read();
            if (!c) return false;
        }
        if (c == '-') {
            sign = -1;
            c = read();
        }
        for (; c >= '0' && c <= '9'; c = read()) {
            num = num * 10 + (c - '0');
        }
        out = num * sign;
        return true;
    }
};

struct RNG {
    uint64_t state;
    RNG(uint64_t seed = 88172645463393265ull) { state = seed ? seed : 88172645463393265ull; }
    inline uint32_t next() {
        // xorshift64*
        uint64_t x = state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        state = x;
        return (uint32_t)((x * 2685821657736338717ULL) >> 32);
    }
    inline uint64_t next64() {
        uint64_t x = state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        state = x;
        return x * 2685821657736338717ULL;
    }
    inline uint32_t next(uint32_t bound) {
        return bound ? next() % bound : 0;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n; int m;
    if (!fs.nextInt(n)) return 0;
    fs.nextInt(m);

    if (m == 0) {
        // No clauses: any assignment is optimal.
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    const int64_t M = m;
    const int64_t L = 3LL * m;

    // Allocate main arrays
    int32_t* lit = (int32_t*)malloc(sizeof(int32_t) * (size_t)L);              // literals array, length 3*m
    int32_t* varOccCount = (int32_t*)calloc((size_t)(n + 2), sizeof(int32_t)); // occurrences per var
    int32_t* posCnt = (int32_t*)calloc((size_t)(n + 2), sizeof(int32_t));      // positive occurrence count
    int32_t* negCnt = (int32_t*)calloc((size_t)(n + 2), sizeof(int32_t));      // negative occurrence count

    // Read clauses and count occurrences
    int32_t a, b, c;
    int64_t p = 0;
    for (int i = 0; i < m; ++i) {
        fs.nextInt(a); fs.nextInt(b); fs.nextInt(c);
        lit[p++] = a;
        lit[p++] = b;
        lit[p++] = c;
        int va = abs(a), vb = abs(b), vc = abs(c);
        if (va >= 1 && va <= n) varOccCount[va]++;
        if (vb >= 1 && vb <= n) varOccCount[vb]++;
        if (vc >= 1 && vc <= n) varOccCount[vc]++;
        if (a > 0) posCnt[va]++; else negCnt[va]++;
        if (b > 0) posCnt[vb]++; else negCnt[vb]++;
        if (c > 0) posCnt[vc]++; else negCnt[vc]++;
    }

    // Build variable occurrence index lists
    int32_t* varStart = (int32_t*)malloc(sizeof(int32_t) * (size_t)(n + 2));
    varStart[1] = 0;
    for (int v = 1; v <= n; ++v) varStart[v + 1] = varStart[v] + varOccCount[v];
    int64_t totalOcc = varStart[n + 1];

    int32_t* varNext = (int32_t*)malloc(sizeof(int32_t) * (size_t)(n + 2));
    memcpy(varNext, varStart, sizeof(int32_t) * (size_t)(n + 2));

    int32_t* varPos = (int32_t*)malloc(sizeof(int32_t) * (size_t)totalOcc);
    for (int64_t i = 0; i < L; ++i) {
        int x = lit[i];
        int v = (x >= 0) ? x : -x;
        int idx = varNext[v]++;
        varPos[idx] = (int32_t)i;
    }

    // Assignment
    uint8_t* assign = (uint8_t*)malloc(sizeof(uint8_t) * (size_t)(n + 2));
    RNG rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] > negCnt[v]) assign[v] = 1;
        else if (posCnt[v] < negCnt[v]) assign[v] = 0;
        else assign[v] = rng.next() & 1u;
    }

    // satCount and unsatisfied set
    uint8_t* satCount = (uint8_t*)malloc(sizeof(uint8_t) * (size_t)m);
    int32_t* posInUnsat = (int32_t*)malloc(sizeof(int32_t) * (size_t)m);
    int32_t* unsat = (int32_t*)malloc(sizeof(int32_t) * (size_t)m);
    int32_t unsatSize = 0;

    for (int i = 0; i < m; ++i) {
        int64_t base = 3LL * i;
        int x = lit[base], y = lit[base + 1], z = lit[base + 2];
        int vx = abs(x), vy = abs(y), vz = abs(z);
        int sx = (x > 0) ? assign[vx] : (uint8_t)(1 - assign[vx]);
        int sy = (y > 0) ? assign[vy] : (uint8_t)(1 - assign[vy]);
        int sz = (z > 0) ? assign[vz] : (uint8_t)(1 - assign[vz]);
        uint8_t s = (uint8_t)(sx + sy + sz);
        satCount[i] = s;
        if (s == 0) {
            posInUnsat[i] = unsatSize;
            unsat[unsatSize++] = i;
        } else {
            posInUnsat[i] = -1;
        }
    }

    auto addUnsat = [&](int cl) {
        if (posInUnsat[cl] != -1) return;
        posInUnsat[cl] = unsatSize;
        unsat[unsatSize++] = cl;
    };
    auto removeUnsat = [&](int cl) {
        int pos = posInUnsat[cl];
        if (pos == -1) return;
        int lastIdx = unsatSize - 1;
        if (pos != lastIdx) {
            int lastCl = unsat[lastIdx];
            unsat[pos] = lastCl;
            posInUnsat[lastCl] = pos;
        }
        unsatSize--;
        posInUnsat[cl] = -1;
    };

    int32_t bestUnsat = unsatSize;
    vector<uint8_t> bestAssign(n + 1);
    for (int v = 1; v <= n; ++v) bestAssign[v] = assign[v];

    // WalkSAT-like local search
    auto t_start = chrono::steady_clock::now();
    const double TIME_BUDGET_SEC = 1.6; // local search time budget
    const int noise_num = 1, noise_den = 5; // 0.2 probability to choose random variable in clause

    auto time_elapsed = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - t_start).count();
    };

    auto computeBreak = [&](int v, int limit) -> int {
        int cnt = 0;
        int32_t st = varStart[v], ed = varStart[v + 1];
        uint8_t val = assign[v];
        for (int32_t i = st; i < ed; ++i) {
            int32_t pos = varPos[i];
            int cl = pos / 3;
            if (satCount[cl] == 1) {
                int lv = lit[pos];
                bool wasTrue = (lv > 0) ? (val != 0) : (val == 0);
                if (wasTrue) {
                    cnt++;
                    if (cnt > limit) return cnt;
                }
            }
        }
        return cnt;
    };

    auto flipVar = [&](int v) {
        uint8_t oldVal = assign[v];
        assign[v] = oldVal ^ 1u;
        int32_t st = varStart[v], ed = varStart[v + 1];
        for (int32_t i = st; i < ed; ++i) {
            int32_t pos = varPos[i];
            int cl = pos / 3;
            uint8_t prev = satCount[cl];
            int lv = lit[pos];
            bool wasTrue = (lv > 0) ? (oldVal != 0) : (oldVal == 0);
            uint8_t nowv;
            if (wasTrue) {
                nowv = (uint8_t)(prev - 1);
                satCount[cl] = nowv;
                if (prev == 1 && nowv == 0) {
                    addUnsat(cl);
                }
            } else {
                nowv = (uint8_t)(prev + 1);
                satCount[cl] = nowv;
                if (prev == 0 && nowv > 0) {
                    removeUnsat(cl);
                }
            }
        }
    };

    int64_t iter = 0;
    while (unsatSize > 0 && time_elapsed() < TIME_BUDGET_SEC) {
        int cl = unsat[rng.next((uint32_t)unsatSize)];
        int64_t base = 3LL * cl;
        int lx = lit[base], ly = lit[base + 1], lz = lit[base + 2];
        int vx = abs(lx), vy = abs(ly), vz = abs(lz);

        int pickVar = -1;

        // With probability noise, pick random variable from the clause
        if ((rng.next() % noise_den) < (uint32_t)noise_num) {
            uint32_t r = rng.next() % 3u;
            pickVar = (r == 0 ? vx : (r == 1 ? vy : vz));
        } else {
            // Compute breaks and choose minimal break
            int bestVar = vx;
            int bestBreak = computeBreak(vx, INT_MAX);
            int b2 = computeBreak(vy, bestBreak);
            int candVar = vy;
            int candBreak = b2;
            if (candBreak < bestBreak || (candBreak == bestBreak && (rng.next() & 1))) {
                bestBreak = candBreak;
                bestVar = candVar;
            }
            int b3 = computeBreak(vz, bestBreak);
            candVar = vz; candBreak = b3;
            if (candBreak < bestBreak || (candBreak == bestBreak && (rng.next() & 1))) {
                bestBreak = candBreak;
                bestVar = candVar;
            }
            pickVar = bestVar;
        }

        flipVar(pickVar);
        if (unsatSize < bestUnsat) {
            bestUnsat = unsatSize;
            for (int v = 1; v <= n; ++v) bestAssign[v] = assign[v];
            if (bestUnsat == 0) break;
        }

        ++iter;
        if ((iter & 4095) == 0 && time_elapsed() >= TIME_BUDGET_SEC) break;
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';

    // Free memory
    free(lit);
    free(varOccCount);
    free(posCnt);
    free(negCnt);
    free(varStart);
    free(varNext);
    free(varPos);
    free(assign);
    free(satCount);
    free(posInUnsat);
    free(unsat);
    return 0;
}