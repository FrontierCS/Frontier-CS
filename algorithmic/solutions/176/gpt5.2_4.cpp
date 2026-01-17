#include <bits/stdc++.h>
using namespace std;

struct XorShift64 {
    uint64_t x;
    XorShift64(uint64_t seed = 88172645463325252ull) : x(seed ? seed : 88172645463325252ull) {}
    uint64_t nextU64() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    uint32_t nextU32() { return (uint32_t)nextU64(); }
    int nextInt(int lo, int hi) { // inclusive
        return lo + (int)(nextU64() % (uint64_t)(hi - lo + 1));
    }
    double nextDouble() { // [0,1)
        return (nextU64() >> 11) * (1.0 / 9007199254740992.0);
    }
};

struct Occ {
    int clause;
    bool pos;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;

    vector<array<int,3>> clauses(m);
    vector<vector<Occ>> occ(n + 1);
    occ.shrink_to_fit();

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; j++) {
            int lit = lits[j];
            int v = abs(lit);
            bool pos = (lit > 0);
            occ[v].push_back({i, pos});
        }
    }

    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    XorShift64 rng(seed);

    vector<uint8_t> assign(n + 1, 0), bestAssign(n + 1, 0);
    vector<uint16_t> satCount(m, 0);
    vector<int> unsat;
    vector<int> posInUnsat(m, -1);

    auto addUnsat = [&](int cl) {
        if (posInUnsat[cl] != -1) return;
        posInUnsat[cl] = (int)unsat.size();
        unsat.push_back(cl);
    };

    auto removeUnsat = [&](int cl) {
        int p = posInUnsat[cl];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posInUnsat[last] = p;
        unsat.pop_back();
        posInUnsat[cl] = -1;
    };

    auto buildState = [&](int &curSat) {
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        curSat = 0;
        for (int i = 0; i < m; i++) {
            int cnt = 0;
            for (int k = 0; k < 3; k++) {
                int lit = clauses[i][k];
                int v = abs(lit);
                bool pos = (lit > 0);
                bool val = pos ? (assign[v] != 0) : (assign[v] == 0);
                cnt += val ? 1 : 0;
            }
            satCount[i] = (uint16_t)cnt;
            if (cnt == 0) addUnsat(i);
            else curSat++;
        }
    };

    auto breakCount = [&](int v) -> int {
        int br = 0;
        bool cur = (assign[v] != 0);
        for (const auto &o : occ[v]) {
            if (satCount[o.clause] == 1) {
                bool litTrue = o.pos ? cur : !cur;
                if (litTrue) br++;
            }
        }
        return br;
    };

    auto flipVar = [&](int v, int &curSat) {
        bool old = (assign[v] != 0);
        for (const auto &o : occ[v]) {
            int cl = o.clause;
            int before = satCount[cl];

            bool oldLitTrue = o.pos ? old : !old;
            bool newLitTrue = !oldLitTrue;

            satCount[cl] = (uint16_t)(before + (newLitTrue ? 1 : -1));
            int after = satCount[cl];

            if (before == 0 && after > 0) {
                removeUnsat(cl);
                curSat++;
            } else if (before > 0 && after == 0) {
                addUnsat(cl);
                curSat--;
            }
        }
        assign[v] = old ? 0 : 1;
    };

    int bestSat = -1;

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 1.80;

    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };

    const int MAX_STEPS_PER_RESTART = 200000;
    const double RANDOM_FLIP_PROB = 0.45;

    while (elapsedSec() < TIME_LIMIT_SEC) {
        for (int i = 1; i <= n; i++) assign[i] = (uint8_t)(rng.nextU32() & 1u);

        int curSat = 0;
        buildState(curSat);

        if (curSat > bestSat) {
            bestSat = curSat;
            bestAssign = assign;
            if (bestSat == m) break;
        }

        for (int step = 0; step < MAX_STEPS_PER_RESTART && elapsedSec() < TIME_LIMIT_SEC; step++) {
            if (unsat.empty()) break;

            int cl = unsat[(size_t)(rng.nextU64() % (uint64_t)unsat.size())];
            int vars[3] = {abs(clauses[cl][0]), abs(clauses[cl][1]), abs(clauses[cl][2])};

            int chosen = vars[0];
            if (rng.nextDouble() < RANDOM_FLIP_PROB) {
                chosen = vars[(int)(rng.nextU64() % 3ull)];
            } else {
                int bestBr = INT_MAX;
                int cand[3];
                int candSz = 0;
                for (int j = 0; j < 3; j++) {
                    int v = vars[j];
                    int br = breakCount(v);
                    if (br < bestBr) {
                        bestBr = br;
                        candSz = 0;
                        cand[candSz++] = v;
                    } else if (br == bestBr) {
                        cand[candSz++] = v;
                    }
                }
                chosen = cand[(int)(rng.nextU64() % (uint64_t)candSz)];
            }

            flipVar(chosen, curSat);

            if (curSat > bestSat) {
                bestSat = curSat;
                bestAssign = assign;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << "\n";
    return 0;
}