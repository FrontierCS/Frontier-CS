#include <bits/stdc++.h>
using namespace std;

struct Occ {
    int cl;
    uint8_t pos;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int,3>> clauses(m);
    vector<vector<Occ>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; j++) {
            int lit = lits[j];
            int v = abs(lit);
            occ[v].push_back(Occ{i, (uint8_t)j});
            if (lit > 0) posCnt[v]++; else negCnt[v]++;
        }
    }

    vector<char> assign(n + 1, 0), bestAssign(n + 1, 0);
    if (m == 0) {
        for (int i = 1; i <= n; i++) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    vector<int> trueCnt(m, 0);
    vector<int> unsat;
    vector<int> posUnsat(m, -1);
    int sat = 0;

    auto addUnsat = [&](int cl) {
        if (posUnsat[cl] == -1) {
            posUnsat[cl] = (int)unsat.size();
            unsat.push_back(cl);
        }
    };
    auto removeUnsat = [&](int cl) {
        int p = posUnsat[cl];
        if (p != -1) {
            int last = unsat.back();
            unsat[p] = last;
            posUnsat[last] = p;
            unsat.pop_back();
            posUnsat[cl] = -1;
        }
    };

    auto rebuildState = [&]() {
        fill(trueCnt.begin(), trueCnt.end(), 0);
        unsat.clear();
        fill(posUnsat.begin(), posUnsat.end(), -1);
        sat = 0;
        for (int i = 0; i < m; i++) {
            int cnt = 0;
            const auto &cl = clauses[i];
            for (int j = 0; j < 3; j++) {
                int lit = cl[j];
                int v = abs(lit);
                bool val = assign[v];
                bool litTrue = (lit > 0) ? val : !val;
                cnt += litTrue ? 1 : 0;
            }
            trueCnt[i] = cnt;
            if (cnt > 0) sat++;
            else addUnsat(i);
        }
    };

    auto applyFlip = [&](int v) {
        char oldVal = assign[v];
        for (const auto &o : occ[v]) {
            int cl = o.cl;
            int lit = clauses[cl][o.pos];
            bool wasTrue = (lit > 0) ? (bool)oldVal : !(bool)oldVal;
            int oldCount = trueCnt[cl];
            int newCount = oldCount + (wasTrue ? -1 : +1);
            trueCnt[cl] = newCount;
            if (oldCount == 0) {
                if (newCount > 0) { sat++; removeUnsat(cl); }
            } else {
                if (newCount == 0) { sat--; addUnsat(cl); }
            }
        }
        assign[v] = !oldVal;
    };

    vector<int> mark(m, 0), tmpCount(m, 0), seenClauses;
    int curMark = 1;

    auto computeDelta = [&](int v) -> int {
        if (occ[v].empty()) return 0;
        curMark++;
        if (curMark == INT_MAX) {
            fill(mark.begin(), mark.end(), 0);
            curMark = 1;
        }
        seenClauses.clear();
        char val = assign[v];
        for (const auto &o : occ[v]) {
            int cl = o.cl;
            if (mark[cl] != curMark) {
                mark[cl] = curMark;
                tmpCount[cl] = trueCnt[cl];
                seenClauses.push_back(cl);
            }
            int lit = clauses[cl][o.pos];
            bool wasTrue = (lit > 0) ? (bool)val : !(bool)val;
            tmpCount[cl] += wasTrue ? -1 : +1;
        }
        int delta = 0;
        for (int cl : seenClauses) {
            bool before = trueCnt[cl] > 0;
            bool after = tmpCount[cl] > 0;
            if (before != after) delta += after ? 1 : -1;
        }
        return delta;
    };

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)new int(1);
    mt19937 rng((uint32_t)seed);

    int bestSat = -1;
    auto considerBest = [&]() {
        if (sat > bestSat) {
            bestSat = sat;
            bestAssign = assign;
        }
    };

    auto initHeuristic = [&]() {
        for (int v = 1; v <= n; v++) assign[v] = (posCnt[v] >= negCnt[v]) ? 1 : 0;
        rebuildState();
    };
    auto initRandom = [&]() {
        for (int v = 1; v <= n; v++) assign[v] = (char)(rng() & 1u);
        rebuildState();
    };

    const double TIME_LIMIT_SEC = 1.85;
    auto t0 = chrono::steady_clock::now();
    auto timeLeft = [&]() -> bool {
        chrono::duration<double> dt = chrono::steady_clock::now() - t0;
        return dt.count() < TIME_LIMIT_SEC;
    };

    auto localSearch = [&](int maxSteps) {
        considerBest();
        for (int step = 0; step < maxSteps; step++) {
            if ((step & 255) == 0 && !timeLeft()) break;
            if (sat == m) break;
            if (unsat.empty()) break;

            int cl = unsat[rng() % unsat.size()];
            const auto &c = clauses[cl];

            int cand[3]; int k = 0;
            for (int j = 0; j < 3; j++) {
                int v = abs(c[j]);
                bool ok = true;
                for (int t = 0; t < k; t++) if (cand[t] == v) { ok = false; break; }
                if (ok) cand[k++] = v;
            }

            int chosenV;
            if ((rng() % 100) < 40) {
                chosenV = cand[rng() % k];
            } else {
                int bestD = INT_MIN;
                int bestVs[3]; int bk = 0;
                for (int i = 0; i < k; i++) {
                    int v = cand[i];
                    int d = computeDelta(v);
                    if (d > bestD) {
                        bestD = d;
                        bk = 0;
                        bestVs[bk++] = v;
                    } else if (d == bestD) {
                        bestVs[bk++] = v;
                    }
                }
                chosenV = bestVs[rng() % bk];
            }

            applyFlip(chosenV);
            considerBest();
        }
    };

    initHeuristic();
    localSearch(20000 + 10 * m);

    while (timeLeft()) {
        initRandom();
        int maxSteps = 30000 + 12 * m;
        localSearch(maxSteps);
        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << "\n";
    return 0;
}