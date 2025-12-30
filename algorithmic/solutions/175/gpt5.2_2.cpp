#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char read() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    inline int nextInt() {
        char c;
        do c = read(); while (c <= ' ' && c);
        int sgn = 1;
        if (c == '-') { sgn = -1; c = read(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        return x * sgn;
    }
};

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    inline uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32() { return (uint32_t)next(); }
};

static inline int evalLit(int lit, const uint8_t* val) {
    int v = (lit > 0) ? lit : -lit;
    return (lit > 0) ? (int)val[v] : (int)(val[v] ^ 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n = fs.nextInt();
    int m = fs.nextInt();

    if (n <= 0) return 0;

    vector<int> A(m), B(m), C(m);

    vector<int> headPos(n + 1, -1), headNeg(n + 1, -1);
    size_t occN = (size_t)3 * (size_t)m;
    vector<int> occClause(occN);
    vector<int> occNext(occN);

    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    size_t occIdx = 0;
    for (int i = 0; i < m; i++) {
        int a = fs.nextInt();
        int b = fs.nextInt();
        int c = fs.nextInt();
        A[i] = a; B[i] = b; C[i] = c;

        int lits[3] = {a, b, c};
        for (int t = 0; t < 3; t++) {
            int lit = lits[t];
            int v = (lit > 0) ? lit : -lit;
            if (lit > 0) posCnt[v]++; else negCnt[v]++;

            int idx = (int)occIdx++;
            occClause[idx] = i;
            if (lit > 0) {
                occNext[idx] = headPos[v];
                headPos[v] = idx;
            } else {
                occNext[idx] = headNeg[v];
                headNeg[v] = idx;
            }
        }
    }

    vector<int> deg(n + 1, 0);
    for (int v = 1; v <= n; v++) deg[v] = posCnt[v] + negCnt[v];

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    SplitMix64 rng(seed);

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    vector<uint8_t> val1(n + 1, 0), val2(n + 1, 0);
    for (int v = 1; v <= n; v++) {
        if (posCnt[v] > negCnt[v]) val1[v] = 1;
        else if (posCnt[v] < negCnt[v]) val1[v] = 0;
        else val1[v] = (uint8_t)(rng.nextU32() & 1);
        val2[v] = (uint8_t)(rng.nextU32() & 1);
    }

    auto satisfiedCountFor = [&](const vector<uint8_t>& vals) -> int {
        const uint8_t* p = vals.data();
        int sat = 0;
        for (int i = 0; i < m; i++) {
            int cnt = evalLit(A[i], p) + evalLit(B[i], p) + evalLit(C[i], p);
            sat += (cnt > 0);
        }
        return sat;
    };

    int sat1 = satisfiedCountFor(val1);
    int sat2 = satisfiedCountFor(val2);

    vector<uint8_t> val = (sat2 > sat1) ? val2 : val1;

    vector<uint8_t> trueCnt(m, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsat;
    unsat.reserve((size_t)m / 8 + 16);

    auto rebuildState = [&]() {
        unsat.clear();
        const uint8_t* p = val.data();
        for (int i = 0; i < m; i++) {
            int cnt = evalLit(A[i], p) + evalLit(B[i], p) + evalLit(C[i], p);
            trueCnt[i] = (uint8_t)cnt;
            if (cnt == 0) {
                posInUnsat[i] = (int)unsat.size();
                unsat.push_back(i);
            } else {
                posInUnsat[i] = -1;
            }
        }
    };

    rebuildState();
    int satisfiedCount = m - (int)unsat.size();

    vector<uint8_t> bestVal = val;
    int bestSatisfied = satisfiedCount;

    // Local search
    long long avgDeg = (n > 0) ? (3LL * m) / n : 1;
    avgDeg = max(1LL, avgDeg);
    const long long targetOps = 25000000LL;
    long long maxFlips = (targetOps * 5) / (6 * avgDeg);
    if (maxFlips < 1000) maxFlips = 1000;
    if (maxFlips > 60000) maxFlips = 60000;

    vector<int8_t> deltaTemp(m, 0);
    vector<int> seen(m, 0);
    int stamp = 1;
    vector<int> touched;
    touched.reserve((size_t)avgDeg + 16);

    auto removeUnsat = [&](int cl) {
        int pos = posInUnsat[cl];
        if (pos == -1) return;
        int last = unsat.back();
        unsat[pos] = last;
        posInUnsat[last] = pos;
        unsat.pop_back();
        posInUnsat[cl] = -1;
    };

    auto addUnsat = [&](int cl) {
        if (posInUnsat[cl] != -1) return;
        posInUnsat[cl] = (int)unsat.size();
        unsat.push_back(cl);
    };

    auto computeDelta = [&](int v) -> int {
        stamp++;
        touched.clear();
        int dir = val[v] ? -1 : +1;

        for (int idx = headPos[v]; idx != -1; idx = occNext[idx]) {
            int cl = occClause[idx];
            if (seen[cl] != stamp) { seen[cl] = stamp; touched.push_back(cl); deltaTemp[cl] = 0; }
            deltaTemp[cl] += (int8_t)dir;
        }
        for (int idx = headNeg[v]; idx != -1; idx = occNext[idx]) {
            int cl = occClause[idx];
            if (seen[cl] != stamp) { seen[cl] = stamp; touched.push_back(cl); deltaTemp[cl] = 0; }
            deltaTemp[cl] += (int8_t)(-dir);
        }

        int ds = 0;
        for (int cl : touched) {
            int d = (int)deltaTemp[cl];
            if (d != 0) {
                int before = (int)trueCnt[cl];
                int after = before + d;
                if (before == 0 && after > 0) ds++;
                else if (before > 0 && after == 0) ds--;
            }
            deltaTemp[cl] = 0;
        }
        return ds;
    };

    auto flipVar = [&](int v) {
        stamp++;
        touched.clear();
        int dir = val[v] ? -1 : +1;

        for (int idx = headPos[v]; idx != -1; idx = occNext[idx]) {
            int cl = occClause[idx];
            if (seen[cl] != stamp) { seen[cl] = stamp; touched.push_back(cl); deltaTemp[cl] = 0; }
            deltaTemp[cl] += (int8_t)dir;
        }
        for (int idx = headNeg[v]; idx != -1; idx = occNext[idx]) {
            int cl = occClause[idx];
            if (seen[cl] != stamp) { seen[cl] = stamp; touched.push_back(cl); deltaTemp[cl] = 0; }
            deltaTemp[cl] += (int8_t)(-dir);
        }

        for (int cl : touched) {
            int d = (int)deltaTemp[cl];
            if (d != 0) {
                int before = (int)trueCnt[cl];
                int after = before + d;
                trueCnt[cl] = (uint8_t)after;

                if (before == 0 && after > 0) {
                    removeUnsat(cl);
                    satisfiedCount++;
                } else if (before > 0 && after == 0) {
                    addUnsat(cl);
                    satisfiedCount--;
                }
            }
            deltaTemp[cl] = 0;
        }

        val[v] ^= 1;
    };

    for (long long it = 0; it < maxFlips; it++) {
        if (unsat.empty()) break;

        int cl = unsat[(size_t)(rng.next() % unsat.size())];
        int l1 = A[cl], l2 = B[cl], l3 = C[cl];
        int v1 = (l1 > 0) ? l1 : -l1;
        int v2 = (l2 > 0) ? l2 : -l2;
        int v3 = (l3 > 0) ? l3 : -l3;

        int chosen = v1;

        if ((rng.nextU32() & 15u) == 0u) {
            int cand[3] = {v1, v2, v3};
            int uniq[3], k = 0;
            for (int i = 0; i < 3; i++) {
                bool ok = true;
                for (int j = 0; j < k; j++) if (uniq[j] == cand[i]) { ok = false; break; }
                if (ok) uniq[k++] = cand[i];
            }

            int bestD = INT_MIN;
            int bestV = uniq[0];
            for (int i = 0; i < k; i++) {
                int v = uniq[i];
                if (deg[v] > 50000) continue; // avoid very heavy evaluations
                int d = computeDelta(v);
                if (d > bestD || (d == bestD && (rng.nextU32() & 1u))) {
                    bestD = d;
                    bestV = v;
                }
            }

            if (bestD == INT_MIN) {
                // fallback to min-degree
                chosen = v1;
                int d0 = deg[v1], d1 = deg[v2], d2 = deg[v3];
                if (d1 < d0 || (d1 == d0 && (rng.nextU32() & 1u))) { chosen = v2; d0 = d1; }
                if (d2 < d0 || (d2 == d0 && (rng.nextU32() & 1u))) { chosen = v3; }
            } else if (bestD < 0 && (rng.nextU32() & 1u)) {
                // random-ish fallback to min-degree candidate
                chosen = v1;
                int d0 = deg[v1], d1 = deg[v2], d2 = deg[v3];
                if (d1 < d0 || (d1 == d0 && (rng.nextU32() & 1u))) { chosen = v2; d0 = d1; }
                if (d2 < d0 || (d2 == d0 && (rng.nextU32() & 1u))) { chosen = v3; }
            } else {
                chosen = bestV;
            }
        } else {
            // choose min-degree variable among the three to keep flips cheap
            chosen = v1;
            int d0 = deg[v1], d1 = deg[v2], d2 = deg[v3];
            if (d1 < d0 || (d1 == d0 && (rng.nextU32() & 1u))) { chosen = v2; d0 = d1; }
            if (d2 < d0 || (d2 == d0 && (rng.nextU32() & 1u))) { chosen = v3; }
        }

        flipVar(chosen);

        if (satisfiedCount > bestSatisfied) {
            bestSatisfied = satisfiedCount;
            bestVal = val;
            if (bestSatisfied == m) break;
        }
    }

    // Output
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}