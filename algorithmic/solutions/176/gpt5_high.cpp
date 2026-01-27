#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<array<int,3>> vars(m);
    vector<array<unsigned char,3>> neg(m);
    vector<int> posCnt(n,0), negCnt(n,0);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int v[3] = {abs(a)-1, abs(b)-1, abs(c)-1};
        unsigned char s[3] = {unsigned char(a<0), unsigned char(b<0), unsigned char(c<0)};
        for (int j = 0; j < 3; ++j) {
            vars[i][j] = v[j];
            neg[i][j] = s[j];
            if (s[j]) negCnt[v[j]]++; else posCnt[v[j]]++;
        }
    }

    // Build adjacency lists: variable -> unique clauses containing it
    vector<vector<int>> varClauses(n);
    varClauses.assign(n, {});
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            varClauses[vars[i][j]].push_back(i);
        }
    }
    for (int v = 0; v < n; ++v) {
        auto &L = varClauses[v];
        sort(L.begin(), L.end());
        L.erase(unique(L.begin(), L.end()), L.end());
    }

    // RNG
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    auto rnd = [&](){ return rng(); };
    auto rnd_int = [&](int l, int r){ std::uniform_int_distribution<int> dist(l, r); return dist(rng); };

    // Time budget in milliseconds
    const int64_t timeBudgetMs = 950;
    auto tStart = chrono::high_resolution_clock::now();
    auto timeExceeded = [&](){
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration_cast<chrono::milliseconds>(now - tStart).count() > timeBudgetMs;
    };

    vector<unsigned char> assign(n, 0), bestAssign(n, 0);
    vector<int> satcnt(m, 0);
    vector<int> breakcost(n, 0);
    vector<int> unsatPos(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    auto litTrue = [&](int i, int j)->int {
        return (assign[vars[i][j]] ^ neg[i][j]) & 1;
    };

    auto removeUnsat = [&](int ci){
        int pos = unsatPos[ci];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        unsatPos[last] = pos;
        unsatList.pop_back();
        unsatPos[ci] = -1;
    };
    auto addUnsat = [&](int ci){
        if (unsatPos[ci] != -1) return;
        unsatPos[ci] = (int)unsatList.size();
        unsatList.push_back(ci);
    };

    auto initialize_state = [&](bool biased)->pair<int, int> {
        // Assignment
        for (int v = 0; v < n; ++v) {
            if (biased) {
                if (posCnt[v] > negCnt[v]) assign[v] = 1;
                else if (posCnt[v] < negCnt[v]) assign[v] = 0;
                else assign[v] = (rnd() & 1);
            } else {
                assign[v] = (rnd() & 1);
            }
        }
        // satcnt and unsat list
        unsatList.clear();
        std::fill(unsatPos.begin(), unsatPos.end(), -1);
        int sat = 0;
        for (int i = 0; i < m; ++i) {
            int s = (litTrue(i,0) + litTrue(i,1) + litTrue(i,2));
            satcnt[i] = s;
            if (s == 0) addUnsat(i);
            else sat++;
        }
        // breakcost
        std::fill(breakcost.begin(), breakcost.end(), 0);
        for (int i = 0; i < m; ++i) {
            if (satcnt[i] == 1) {
                for (int j = 0; j < 3; ++j) {
                    if (litTrue(i,j)) {
                        breakcost[vars[i][j]]++;
                        break;
                    }
                }
            }
        }
        return {sat, (int)unsatList.size()};
    };

    auto flipVar = [&](int v, int &sat){
        // For each clause containing v, compute changes atomically
        for (int ci : varClauses[v]) {
            int tb0 = litTrue(ci,0);
            int tb1 = litTrue(ci,1);
            int tb2 = litTrue(ci,2);
            int k_old = tb0 + tb1 + tb2;

            int ta0 = tb0 ^ (vars[ci][0] == v);
            int ta1 = tb1 ^ (vars[ci][1] == v);
            int ta2 = tb2 ^ (vars[ci][2] == v);
            int k_new = ta0 + ta1 + ta2;

            // Update breakcost for unique-literal clauses
            if (k_old == 1) {
                if (tb0) breakcost[vars[ci][0]]--;
                else if (tb1) breakcost[vars[ci][1]]--;
                else breakcost[vars[ci][2]]--;
            }
            if (k_new == 1) {
                if (ta0) breakcost[vars[ci][0]]++;
                else if (ta1) breakcost[vars[ci][1]]++;
                else breakcost[vars[ci][2]]++;
            }

            if (k_old == 0 && k_new > 0) {
                sat++;
                removeUnsat(ci);
            } else if (k_old > 0 && k_new == 0) {
                sat--;
                addUnsat(ci);
            }
            satcnt[ci] = k_new;
        }
        assign[v] ^= 1;
    };

    // Initial run biased
    auto initRes = initialize_state(true);
    int currentSat = initRes.first;
    int bestSat = currentSat;
    bestAssign = assign;

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    const int NOISE_PERMIL = 350; // 35% noise
    int plateauLimitBase = max(2000, n * 2);

    bool first = true;
    while (!timeExceeded()) {
        if (!first) {
            initRes = initialize_state(false);
            currentSat = initRes.first;
        }
        first = false;
        if (currentSat > bestSat) { bestSat = currentSat; bestAssign = assign; if (bestSat == m) break; }

        int stepsSinceImprovement = 0;
        int plateauLimit = plateauLimitBase;
        int guard = 0;

        while (!timeExceeded()) {
            if (currentSat == m) { bestSat = currentSat; bestAssign = assign; break; }
            if (unsatList.empty()) { bestSat = currentSat; bestAssign = assign; break; }

            // pick random unsatisfied clause
            int ci = unsatList[rnd_int(0, (int)unsatList.size()-1)];
            // candidates: unique variables in this clause
            int cand[3], cnum = 0;
            for (int j = 0; j < 3; ++j) {
                int v = vars[ci][j];
                bool seen = false;
                for (int k = 0; k < cnum; ++k) if (cand[k] == v) { seen = true; break; }
                if (!seen) cand[cnum++] = v;
            }

            // choose variable
            int chosen = cand[0];
            int zeros[3], zc = 0;
            int minBreak = INT_MAX;
            int minIdxs[3], mic = 0;
            for (int i = 0; i < cnum; ++i) {
                int v = cand[i];
                int bc = breakcost[v];
                if (bc == 0) zeros[zc++] = v;
                if (bc < minBreak) {
                    minBreak = bc;
                    mic = 0;
                    minIdxs[mic++] = v;
                } else if (bc == minBreak) {
                    if (mic < 3) minIdxs[mic++] = v;
                }
            }
            if (zc > 0) {
                chosen = zeros[rnd_int(0, zc-1)];
            } else {
                if ((int)(rnd() % 1000) < NOISE_PERMIL) {
                    chosen = cand[rnd_int(0, cnum-1)];
                } else {
                    chosen = minIdxs[rnd_int(0, mic-1)];
                }
            }

            flipVar(chosen, currentSat);

            if (currentSat > bestSat) {
                bestSat = currentSat;
                bestAssign = assign;
                stepsSinceImprovement = 0;
                if (bestSat == m) break;
            } else {
                stepsSinceImprovement++;
                if (stepsSinceImprovement > plateauLimit) {
                    break; // restart
                }
            }

            // periodic soft time check
            guard++;
            if ((guard & 4095) == 0 && timeExceeded()) break;
        }
        if (bestSat == m || timeExceeded()) break;
    }

    // Output best assignment found
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';
    return 0;
}