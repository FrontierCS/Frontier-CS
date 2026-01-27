#include <bits/stdc++.h>
using namespace std;

struct Occurrence {
    int clause;
    bool pos;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    
    vector<vector<pair<int,bool>>> clauses; // processed (deduplicated, tautologies removed)
    clauses.reserve(m);
    vector<int> posCnt(n+1, 0), negCnt(n+1, 0);
    
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        vector<pair<int,bool>> tmp;
        tmp.reserve(3);
        bool taut = false;
        for (int k = 0; k < 3; ++k) {
            int lit = lits[k];
            int var = abs(lit);
            bool pos = lit > 0;
            bool foundSame = false, foundOpp = false;
            for (auto &p : tmp) {
                if (p.first == var) {
                    if (p.second == pos) foundSame = true;
                    else foundOpp = true;
                }
            }
            if (foundOpp) { taut = true; break; }
            if (!foundSame) tmp.push_back({var, pos});
        }
        if (taut) continue;
        if (tmp.empty()) continue; // degenerate, ignore
        for (auto &p : tmp) {
            if (p.second) posCnt[p.first]++; else negCnt[p.first]++;
        }
        clauses.push_back(move(tmp));
    }
    
    int M = (int)clauses.size();
    vector<vector<Occurrence>> occ(n+1);
    for (int c = 0; c < M; ++c) {
        for (auto &lit : clauses[c]) {
            int v = lit.first; bool p = lit.second;
            occ[v].push_back({c, p});
        }
    }
    
    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto randint = [&](int l, int r)->int { // inclusive
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };
    auto randprob = [&]()->double {
        uniform_real_distribution<double> dist(0.0, 1.0);
        return dist(rng);
    };
    
    vector<char> assign(n+1, 0), bestAssign(n+1, 0);
    for (int i = 1; i <= n; ++i) {
        assign[i] = (posCnt[i] >= negCnt[i]) ? 1 : 0;
    }
    
    vector<int> satCount(M, 0);
    vector<int> unsatPos(M, -1);
    vector<int> unsat;
    unsat.reserve(M);
    auto addUnsat = [&](int c) {
        if (unsatPos[c] != -1) return;
        unsatPos[c] = (int)unsat.size();
        unsat.push_back(c);
    };
    auto removeUnsat = [&](int c) {
        int p = unsatPos[c];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        unsatPos[last] = p;
        unsat.pop_back();
        unsatPos[c] = -1;
    };
    
    auto recompute = [&](vector<char>& asg) {
        fill(satCount.begin(), satCount.end(), 0);
        fill(unsatPos.begin(), unsatPos.end(), -1);
        unsat.clear();
        for (int c = 0; c < M; ++c) {
            int cnt = 0;
            for (auto &lit : clauses[c]) {
                int v = lit.first; bool p = lit.second;
                if ((asg[v] ? 1 : 0) == (p ? 1 : 0)) cnt++;
            }
            satCount[c] = cnt;
            if (cnt == 0) addUnsat(c);
        }
    };
    
    recompute(assign);
    int bestS = M - (int)unsat.size();
    bestAssign = assign;
    
    if (M > 0 && !unsat.empty()) {
        auto start = chrono::steady_clock::now();
        long long budget_ms = 350; // time budget
        const double noise = 0.45;
        
        int step = 0;
        int stall = 0;
        int stallThreshold = 5000;
        
        while (true) {
            auto now = chrono::steady_clock::now();
            long long elapsed = chrono::duration_cast<chrono::milliseconds>(now - start).count();
            if (elapsed > budget_ms) break;
            if (unsat.empty()) break;
            
            int cidx = unsat[randint(0, (int)unsat.size()-1)];
            auto &cl = clauses[cidx];
            int k = (int)cl.size();
            if (k == 0) { // shouldn't happen
                removeUnsat(cidx);
                continue;
            }
            
            // Candidates
            int bestVar = cl[0].first;
            int minBreak = INT_MAX;
            int bestMake = -1;
            vector<int> candZeroBreak;
            
            // Evaluate break/make for each candidate variable
            int vars[3] = {0,0,0};
            for (int i = 0; i < k; ++i) vars[i] = cl[i].first;
            for (int i = 0; i < k; ++i) {
                int v = vars[i];
                int brk = 0, mk = 0;
                for (auto &oc : occ[v]) {
                    int ci = oc.clause;
                    bool litTrue = (assign[v] ? 1 : 0) == (oc.pos ? 1 : 0);
                    if (satCount[ci] == 0) {
                        mk++;
                    } else if (satCount[ci] == 1 && litTrue) {
                        brk++;
                    }
                }
                if (brk == 0) candZeroBreak.push_back(v);
                if (brk < minBreak || (brk == minBreak && mk > bestMake) || (brk == minBreak && mk == bestMake && randint(0,1))) {
                    minBreak = brk;
                    bestMake = mk;
                    bestVar = v;
                }
            }
            
            int chosenVar;
            if (!candZeroBreak.empty()) {
                chosenVar = candZeroBreak[randint(0, (int)candZeroBreak.size()-1)];
            } else {
                if (randprob() < noise) {
                    chosenVar = vars[randint(0, k-1)];
                } else {
                    chosenVar = bestVar;
                }
            }
            
            // Flip chosenVar
            char oldVal = assign[chosenVar];
            assign[chosenVar] ^= 1;
            for (auto &oc : occ[chosenVar]) {
                int ci = oc.clause;
                bool beforeTrue = (oldVal ? 1 : 0) == (oc.pos ? 1 : 0);
                if (beforeTrue) {
                    // lose a true literal
                    if (satCount[ci] == 1) {
                        satCount[ci]--;
                        addUnsat(ci);
                    } else {
                        satCount[ci]--;
                    }
                } else {
                    // gain a true literal
                    if (satCount[ci] == 0) {
                        satCount[ci]++;
                        removeUnsat(ci);
                    } else {
                        satCount[ci]++;
                    }
                }
            }
            
            int curS = M - (int)unsat.size();
            if (curS > bestS) {
                bestS = curS;
                bestAssign = assign;
                stall = 0;
            } else {
                stall++;
            }
            step++;
            
            if (stall >= stallThreshold) {
                // random restart
                for (int i = 1; i <= n; ++i) {
                    // bias towards majority a bit
                    if (randprob() < 0.7) assign[i] = (posCnt[i] >= negCnt[i]) ? 1 : 0;
                    else assign[i] = (char)(randint(0,1));
                }
                recompute(assign);
                stall = 0;
            }
        }
    }
    
    // Output best assignment
    for (int i = 1; i <= n; ++i) {
        cout << (int)bestAssign[i] << (i == n ? '\n' : ' ');
    }
    return 0;
}