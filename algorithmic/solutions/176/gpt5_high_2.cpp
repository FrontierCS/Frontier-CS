#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    vector<array<int,3>> clauses(m);
    vector<vector<int>> varClauses(n);
    vector<int> posCount(n, 0), negCount(n, 0);
    
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int v = abs(lit) - 1;
            if (v >= 0 && v < n) {
                varClauses[v].push_back(i);
                if (lit > 0) posCount[v]++; else negCount[v]++;
            }
        }
    }
    for (int v = 0; v < n; ++v) {
        auto &vec = varClauses[v];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }
    
    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)new int);
    auto rnd_bool = [&]() -> int { return (int)(rng() & 1u); };
    auto rnd_real = [&]() -> double { return (double)rng() / (double)rng.max(); };
    
    vector<unsigned char> assign(n, 0);
    for (int v = 0; v < n; ++v) {
        if (posCount[v] > negCount[v]) assign[v] = 1;
        else if (posCount[v] < negCount[v]) assign[v] = 0;
        else assign[v] = rnd_bool();
    }
    
    auto lit_true = [&](int lit, const vector<unsigned char>& a) -> int {
        int v = abs(lit) - 1;
        unsigned char val = a[v];
        if (lit > 0) return val ? 1 : 0;
        else return val ? 0 : 1;
    };
    
    vector<int> satCount(m, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);
    
    auto addUnsat = [&](int c) {
        if (posInUnsat[c] != -1) return;
        posInUnsat[c] = (int)unsatList.size();
        unsatList.push_back(c);
    };
    auto removeUnsat = [&](int c) {
        int pos = posInUnsat[c];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        posInUnsat[last] = pos;
        unsatList.pop_back();
        posInUnsat[c] = -1;
    };
    
    auto computeClauseCount = [&](int cid, const vector<unsigned char>& a) -> int {
        auto &cl = clauses[cid];
        int cnt = 0;
        cnt += lit_true(cl[0], a);
        cnt += lit_true(cl[1], a);
        cnt += lit_true(cl[2], a);
        return cnt;
    };
    auto computeClauseCountIfFlip = [&](int cid, int flipVar, const vector<unsigned char>& a) -> int {
        auto &cl = clauses[cid];
        int cnt = 0;
        for (int j = 0; j < 3; ++j) {
            int lit = cl[j];
            int v = abs(lit) - 1;
            unsigned char val = a[v];
            if (v == flipVar) val ^= 1;
            int sat = (lit > 0) ? (val ? 1 : 0) : (val ? 0 : 1);
            cnt += sat;
        }
        return cnt;
    };
    
    auto rebuildState = [&]() {
        fill(satCount.begin(), satCount.end(), 0);
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        unsatList.clear();
        for (int i = 0; i < m; ++i) {
            int cnt = computeClauseCount(i, assign);
            satCount[i] = cnt;
            if (cnt == 0) addUnsat(i);
        }
    };
    
    rebuildState();
    
    vector<unsigned char> bestAssign = assign;
    int bestUnsat = (int)unsatList.size();
    
    const double TIME_LIMIT = 0.95; // seconds
    auto startTime = chrono::steady_clock::now();
    auto elapsed = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - startTime).count();
    };
    
    auto calcDelta = [&](int var) -> int {
        int delta = 0;
        for (int cid : varClauses[var]) {
            int oldSat = (satCount[cid] > 0) ? 1 : 0;
            int newCnt = computeClauseCountIfFlip(cid, var, assign);
            int newSat = (newCnt > 0) ? 1 : 0;
            delta += (newSat - oldSat);
        }
        return delta;
    };
    
    auto flipVar = [&](int var) {
        assign[var] ^= 1;
        for (int cid : varClauses[var]) {
            int oldCnt = satCount[cid];
            int newCnt = computeClauseCount(cid, assign);
            if (oldCnt == 0 && newCnt > 0) {
                removeUnsat(cid);
            } else if (oldCnt > 0 && newCnt == 0) {
                addUnsat(cid);
            }
            satCount[cid] = newCnt;
        }
    };
    
    const double NOISE_P = 0.4;
    const int STAGNATION_LIMIT = 4000;
    int restartCount = 0;
    int stepsSinceImprove = 0;
    
    while (elapsed() < TIME_LIMIT) {
        if (unsatList.empty()) break;
        int steps = 0;
        int lastImproveStep = 0;
        while (elapsed() < TIME_LIMIT && !unsatList.empty()) {
            steps++;
            stepsSinceImprove++;
            int cid = unsatList[rng() % unsatList.size()];
            // Collect unique variables from this clause
            array<int,3> lits = clauses[cid];
            int cand[3];
            int candSz = 0;
            for (int j = 0; j < 3; ++j) {
                int v = abs(lits[j]) - 1;
                bool exists = false;
                for (int k = 0; k < candSz; ++k) if (cand[k] == v) { exists = true; break; }
                if (!exists) cand[candSz++] = v;
            }
            int chosenVar;
            if (rnd_real() < NOISE_P) {
                chosenVar = cand[rng() % candSz];
            } else {
                int bestDeltaVar = cand[0];
                int bestDeltaVal = INT_MIN;
                int ties[3]; int tieCnt = 0;
                for (int i = 0; i < candSz; ++i) {
                    int v = cand[i];
                    int d = calcDelta(v);
                    if (d > bestDeltaVal) {
                        bestDeltaVal = d;
                        tieCnt = 0;
                        ties[tieCnt++] = v;
                    } else if (d == bestDeltaVal) {
                        ties[tieCnt++] = v;
                    }
                }
                chosenVar = ties[rng() % tieCnt];
            }
            flipVar(chosenVar);
            
            int curUnsat = (int)unsatList.size();
            if (curUnsat < bestUnsat) {
                bestUnsat = curUnsat;
                bestAssign = assign;
                lastImproveStep = steps;
                stepsSinceImprove = 0;
                if (bestUnsat == 0) break;
            }
            if (steps - lastImproveStep > STAGNATION_LIMIT) break;
        }
        if (unsatList.empty() || elapsed() >= TIME_LIMIT) break;
        // Restart
        restartCount++;
        if (restartCount % 2 == 1) {
            for (int v = 0; v < n; ++v) assign[v] = rnd_bool();
        } else {
            for (int v = 0; v < n; ++v) {
                if (posCount[v] > negCount[v]) assign[v] = 1;
                else if (posCount[v] < negCount[v]) assign[v] = 0;
                else assign[v] = rnd_bool();
                if ((rng() & 7u) == 0) assign[v] ^= 1; // small noise
            }
        }
        rebuildState();
        if ((int)unsatList.size() < bestUnsat) {
            bestUnsat = (int)unsatList.size();
            bestAssign = assign;
        }
    }
    
    // Output best assignment found
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';
    return 0;
}