#include <bits/stdc++.h>
using namespace std;

struct Occ {
    int ci;
    int sign; // +1 for x, -1 for !x
};

static inline uint64_t splitmix64(uint64_t &x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int,3>> clauses(m);
    vector<vector<Occ>> occ(n + 1);
    occ.shrink_to_fit();

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int k = 0; k < 3; k++) {
            int lit = lits[k];
            int v = abs(lit);
            int sgn = (lit > 0) ? +1 : -1;
            occ[v].push_back({i, sgn});
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

    // RNG
    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    uint64_t smx = seed;
    auto rnd_u32 = [&]() -> uint32_t { return (uint32_t)splitmix64(smx); };
    auto rnd_int = [&](int l, int r) -> int { // inclusive
        return l + (int)(rnd_u32() % (uint32_t)(r - l + 1));
    };
    auto rnd01 = [&]() -> double {
        return (rnd_u32() >> 8) * (1.0 / 16777216.0); // 24-bit
    };

    vector<uint8_t> val(n + 1, 0);
    vector<int> trueCount(m, 0);
    vector<int> unsatList;
    vector<int> posInUnsat(m, -1);
    int satCount = 0;

    auto addUnsat = [&](int ci) {
        if (posInUnsat[ci] != -1) return;
        posInUnsat[ci] = (int)unsatList.size();
        unsatList.push_back(ci);
    };
    auto removeUnsat = [&](int ci) {
        int p = posInUnsat[ci];
        if (p == -1) return;
        int last = unsatList.back();
        unsatList[p] = last;
        posInUnsat[last] = p;
        unsatList.pop_back();
        posInUnsat[ci] = -1;
    };

    auto rebuildState = [&]() {
        fill(trueCount.begin(), trueCount.end(), 0);
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        unsatList.clear();
        satCount = 0;

        for (int i = 0; i < m; i++) {
            int cnt = 0;
            for (int k = 0; k < 3; k++) {
                int lit = clauses[i][k];
                int v = abs(lit);
                bool vval = val[v] != 0;
                bool ltrue = (lit > 0) ? vval : !vval;
                cnt += (int)ltrue;
            }
            trueCount[i] = cnt;
            if (cnt > 0) satCount++;
            else addUnsat(i);
        }
    };

    auto flipVar = [&](int v) {
        uint8_t oldVal = val[v];
        uint8_t newVal = oldVal ^ 1;
        val[v] = newVal;

        for (const auto &e : occ[v]) {
            int ci = e.ci;
            int beforeCnt = trueCount[ci];
            bool beforeSat = beforeCnt > 0;

            bool oldTruth = (e.sign == +1) ? (oldVal != 0) : (oldVal == 0);
            // newTruth is !oldTruth
            if (oldTruth) trueCount[ci]--;
            else trueCount[ci]++;

            int afterCnt = trueCount[ci];
            bool afterSat = afterCnt > 0;

            if (beforeSat && !afterSat) {
                satCount--;
                addUnsat(ci);
            } else if (!beforeSat && afterSat) {
                satCount++;
                removeUnsat(ci);
            }
        }
    };

    vector<int> mark(m, 0);
    int curMark = 1;

    auto computeDelta = [&](int v) -> int {
        int myMark = curMark++;
        if (curMark == INT_MAX) {
            fill(mark.begin(), mark.end(), 0);
            curMark = 1;
            myMark = curMark++;
        }

        vector<int> touched;
        touched.reserve(occ[v].size());
        for (const auto &e : occ[v]) {
            int ci = e.ci;
            if (mark[ci] != myMark) {
                mark[ci] = myMark;
                touched.push_back(ci);
            }
        }

        bool newV = (val[v] == 0);
        int delta = 0;
        for (int ci : touched) {
            bool oldSat = trueCount[ci] > 0;
            int newCnt = 0;
            for (int k = 0; k < 3; k++) {
                int lit = clauses[ci][k];
                int var = abs(lit);
                bool vval = (var == v) ? newV : (val[var] != 0);
                bool ltrue = (lit > 0) ? vval : !vval;
                newCnt += (int)ltrue;
            }
            bool newSat = newCnt > 0;
            delta += (int)newSat - (int)oldSat;
        }
        return delta;
    };

    vector<uint8_t> bestVal(n + 1, 0);
    int bestSat = -1;

    auto randomInit = [&]() {
        for (int i = 1; i <= n; i++) val[i] = (uint8_t)(rnd_u32() & 1);
        rebuildState();
    };

    const double pRandom = 0.35;
    const int maxRestarts = 30;
    const int maxSteps = 20000;

    for (int restart = 0; restart < maxRestarts; restart++) {
        randomInit();

        if (satCount > bestSat) {
            bestSat = satCount;
            bestVal = val;
            if (bestSat == m) break;
        }

        for (int step = 0; step < maxSteps && satCount < m; step++) {
            if (unsatList.empty()) break;

            int ci = unsatList[rnd_int(0, (int)unsatList.size() - 1)];
            auto lits = clauses[ci];

            int candVars[3] = {abs(lits[0]), abs(lits[1]), abs(lits[2])};

            int chosenV = candVars[rnd_int(0, 2)];
            if (rnd01() >= pRandom) {
                // choose best delta among unique vars in clause
                int uniqueVars[3];
                int ucnt = 0;
                for (int k = 0; k < 3; k++) {
                    int v = candVars[k];
                    bool exists = false;
                    for (int t = 0; t < ucnt; t++) if (uniqueVars[t] == v) { exists = true; break; }
                    if (!exists) uniqueVars[ucnt++] = v;
                }

                int bestDelta = INT_MIN;
                vector<int> bestCands;
                bestCands.reserve(3);

                for (int t = 0; t < ucnt; t++) {
                    int v = uniqueVars[t];
                    int d = computeDelta(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        bestCands.clear();
                        bestCands.push_back(v);
                    } else if (d == bestDelta) {
                        bestCands.push_back(v);
                    }
                }
                chosenV = bestCands[rnd_int(0, (int)bestCands.size() - 1)];
            }

            flipVar(chosenV);

            if (satCount > bestSat) {
                bestSat = satCount;
                bestVal = val;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
    }

    // Final greedy improvement on best
    val = bestVal;
    rebuildState();
    bool improved = true;
    while (improved) {
        improved = false;
        for (int v = 1; v <= n; v++) {
            int d = computeDelta(v);
            if (d > 0) {
                flipVar(v);
                improved = true;
            }
        }
    }
    if (satCount >= bestSat) {
        bestSat = satCount;
        bestVal = val;
    }

    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << ' ';
        cout << (bestVal[i] ? 1 : 0);
    }
    cout << "\n";
    return 0;
}