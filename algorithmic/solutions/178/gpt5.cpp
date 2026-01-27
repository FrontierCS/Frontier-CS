#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[3];
    bool s[3]; // true if positive literal
};

struct Occ { int ci, j; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<Occ>> occ(n);
    vector<int> posCnt(n, 0), negCnt(n, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            bool pos = x > 0;
            int var = abs(x) - 1;
            if (pos) posCnt[var]++; else negCnt[var]++;
            clauses[i].v[j] = var;
            clauses[i].s[j] = pos;
            occ[var].push_back({i, j});
        }
    }

    // Random generator
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    auto rand_u = [&](uint64_t l, uint64_t r)->uint64_t { // inclusive [l,r]
        std::uniform_int_distribution<uint64_t> dist(l, r);
        return dist(rng);
    };
    auto rand01 = [&]()->double {
        std::uniform_real_distribution<double> dist(0.0, 1.0);
        return dist(rng);
    };

    // Data structures for search
    vector<char> assign(n, 0), bestAssign(n, 0);
    vector<int> clauseTrueCount(m, 0);
    vector<int> unsatPos(m, -1);
    vector<int> unsatList; unsatList.reserve(m);

    auto addUnsat = [&](int ci){
        if (unsatPos[ci] == -1) {
            unsatPos[ci] = (int)unsatList.size();
            unsatList.push_back(ci);
        }
    };
    auto removeUnsat = [&](int ci){
        int p = unsatPos[ci];
        if (p != -1) {
            int last = unsatList.back();
            unsatList[p] = last;
            unsatPos[last] = p;
            unsatList.pop_back();
            unsatPos[ci] = -1;
        }
    };

    auto initAssignment = [&](int mode){ // mode 0: majority, 1: random
        if (mode == 0) {
            for (int i = 0; i < n; ++i) {
                if (posCnt[i] > negCnt[i]) assign[i] = 1;
                else if (posCnt[i] < negCnt[i]) assign[i] = 0;
                else assign[i] = (char)(rand_u(0,1));
            }
        } else {
            for (int i = 0; i < n; ++i) assign[i] = (char)(rand_u(0,1));
        }
        // compute clause true counts and unsatisfied set
        if (m) {
            fill(clauseTrueCount.begin(), clauseTrueCount.end(), 0);
            fill(unsatPos.begin(), unsatPos.end(), -1);
            unsatList.clear();
            for (int ci = 0; ci < m; ++ci) {
                int t = 0;
                for (int j = 0; j < 3; ++j) {
                    int v = clauses[ci].v[j];
                    bool s = clauses[ci].s[j];
                    bool litTrue = s ? (assign[v] != 0) : (assign[v] == 0);
                    if (litTrue) ++t;
                }
                clauseTrueCount[ci] = t;
                if (t == 0) addUnsat(ci);
            }
        }
    };

    auto satisfiedCount = [&]()->int {
        return m - (int)unsatList.size();
    };

    // Flip function
    auto flipVar = [&](int v){
        // update counts for all clauses containing v
        for (const auto &oc : occ[v]) {
            int ci = oc.ci, j = oc.j;
            bool litWasTrue = clauses[ci].s[j] ? (assign[v] != 0) : (assign[v] == 0);
            int t = clauseTrueCount[ci];
            if (litWasTrue) {
                --t;
                if (t == 0) addUnsat(ci);
            } else {
                ++t;
                if (t == 1) removeUnsat(ci);
            }
            clauseTrueCount[ci] = t;
        }
        assign[v] = !assign[v];
    };

    // Aggregator for computing delta and break counts with duplicate handling
    vector<int> stamp(m, 0);
    vector<unsigned char> aggA(m, 0), aggO(m, 0);
    int stampCounter = 0;
    vector<int> touched;
    touched.reserve(64);

    auto computeDeltaBreak = [&](int v)->pair<int,int> {
        int delta = 0, brk = 0;
        if (m == 0) return {0,0};
        ++stampCounter;
        if (stampCounter == INT_MAX) {
            fill(stamp.begin(), stamp.end(), 0);
            stampCounter = 1;
        }
        touched.clear();
        char aval = assign[v];
        for (const auto &oc : occ[v]) {
            int ci = oc.ci, j = oc.j;
            if (stamp[ci] != stampCounter) {
                stamp[ci] = stampCounter;
                aggA[ci] = 0;
                aggO[ci] = 0;
                touched.push_back(ci);
            }
            bool litTrue = clauses[ci].s[j] ? (aval != 0) : (aval == 0);
            aggO[ci]++;
            if (litTrue) aggA[ci]++;
        }
        for (int ci : touched) {
            int t = clauseTrueCount[ci];
            int A = aggA[ci];
            int O = aggO[ci];
            int tprime = t + O - 2 * A;
            if (t == 0 && tprime > 0) delta++;
            else if (t > 0 && tprime == 0) { delta--; brk++; }
        }
        return {delta, brk};
    };

    // Timing control
    auto startTime = chrono::steady_clock::now();
    auto timeLimit = chrono::milliseconds(900);
    auto deadline = startTime + timeLimit;

    // Initial best
    if (m == 0) {
        // Any assignment acceptable
        for (int i = 0; i < n; ++i) cout << 0 << (i + 1 == n ? '\n' : ' ');
        return 0;
    }

    int bestSatisfied = -1;

    // Try multiple restarts until time expires or all satisfied
    int restart = 0;
    const int maxStepsPerRestart = 30000;

    while (chrono::steady_clock::now() < deadline) {
        int mode = (restart == 0) ? 0 : 1; // first majority, then random
        initAssignment(mode);
        int currentSatisfied = satisfiedCount();
        if (currentSatisfied > bestSatisfied) {
            bestSatisfied = currentSatisfied;
            bestAssign = assign;
            if (bestSatisfied == m) break;
        }

        int steps = 0;
        int lastImprovedStep = 0;
        const double walkProb = 0.8;
        const double walkNoise = 0.35;

        while (steps < maxStepsPerRestart) {
            if ((steps & 127) == 0 && chrono::steady_clock::now() >= deadline) break;
            if (unsatList.empty()) break;

            bool didFlip = false;
            if (rand01() < walkProb) {
                // WalkSAT step
                int ci = unsatList[(size_t)rand_u(0, unsatList.size() - 1)];
                // Gather unique variables from this clause
                int varsInClause[3] = {clauses[ci].v[0], clauses[ci].v[1], clauses[ci].v[2]};
                int uniqueVars[3];
                int ucnt = 0;
                for (int k = 0; k < 3; ++k) {
                    int v = varsInClause[k];
                    bool seen = false;
                    for (int t = 0; t < ucnt; ++t) if (uniqueVars[t] == v) { seen = true; break; }
                    if (!seen) uniqueVars[ucnt++] = v;
                }
                int zeroBreakVars[3]; int zbCnt = 0;
                int bestBreak = INT_MAX;
                int bestBreakVars[3]; int bbCnt = 0;
                for (int t = 0; t < ucnt; ++t) {
                    int v = uniqueVars[t];
                    auto db = computeDeltaBreak(v);
                    int brk = db.second;
                    if (brk == 0) zeroBreakVars[zbCnt++] = v;
                    if (brk < bestBreak) { bestBreak = brk; bbCnt = 0; bestBreakVars[bbCnt++] = v; }
                    else if (brk == bestBreak) { bestBreakVars[bbCnt++] = v; }
                }
                int chosenVar;
                if (zbCnt > 0) {
                    chosenVar = zeroBreakVars[(int)rand_u(0, zbCnt - 1)];
                } else {
                    if (rand01() < walkNoise) {
                        chosenVar = uniqueVars[(int)rand_u(0, ucnt - 1)];
                    } else {
                        chosenVar = bestBreakVars[(int)rand_u(0, bbCnt - 1)];
                    }
                }
                flipVar(chosenVar);
                didFlip = true;
            } else {
                // GSAT-like step: choose variable with best delta improvement
                int bestDelta = INT_MIN;
                int bestVars[64];
                int bcnt = 0;
                for (int v = 0; v < n; ++v) {
                    auto db = computeDeltaBreak(v);
                    int d = db.first;
                    if (d > bestDelta) { bestDelta = d; bcnt = 0; bestVars[bcnt++] = v; }
                    else if (d == bestDelta) { bestVars[bcnt++] = v; }
                }
                int chosenVar = -1;
                if (bestDelta > 0) {
                    chosenVar = bestVars[(int)rand_u(0, bcnt - 1)];
                } else {
                    // No improving move; fallback to WalkSAT-like move
                    int ci = unsatList[(size_t)rand_u(0, unsatList.size() - 1)];
                    int varsInClause[3] = {clauses[ci].v[0], clauses[ci].v[1], clauses[ci].v[2]};
                    int uniqueVars[3]; int ucnt = 0;
                    for (int k = 0; k < 3; ++k) {
                        int v = varsInClause[k];
                        bool seen = false;
                        for (int t = 0; t < ucnt; ++t) if (uniqueVars[t] == v) { seen = true; break; }
                        if (!seen) uniqueVars[ucnt++] = v;
                    }
                    // Prefer minimal break
                    int bestBreak = INT_MAX; int bestBreakVars[3]; int bbCnt = 0;
                    for (int t = 0; t < ucnt; ++t) {
                        int v = uniqueVars[t];
                        int brk = computeDeltaBreak(v).second;
                        if (brk < bestBreak) { bestBreak = brk; bbCnt = 0; bestBreakVars[bbCnt++] = v; }
                        else if (brk == bestBreak) { bestBreakVars[bbCnt++] = v; }
                    }
                    chosenVar = bestBreakVars[(int)rand_u(0, bbCnt - 1)];
                }
                flipVar(chosenVar);
                didFlip = true;
            }

            if (didFlip) {
                ++steps;
                int sc = satisfiedCount();
                if (sc > bestSatisfied) {
                    bestSatisfied = sc;
                    bestAssign = assign;
                    lastImprovedStep = steps;
                    if (bestSatisfied == m) break;
                }
                // Early restart if stuck
                if (steps - lastImprovedStep > 2000) break;
            }
        }

        if (bestSatisfied == m) break;
        ++restart;
    }

    if (bestSatisfied < 0) {
        // Fallback: output zeros
        for (int i = 0; i < n; ++i) cout << 0 << (i + 1 == n ? '\n' : ' ');
        return 0;
    }
    for (int i = 0; i < n; ++i) cout << int(bestAssign[i]) << (i + 1 == n ? '\n' : ' ');
    return 0;
}