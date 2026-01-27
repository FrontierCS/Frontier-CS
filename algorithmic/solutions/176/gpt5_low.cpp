#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<array<int,3>> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a,b,c; cin >> a >> b >> c;
        clauses[i] = {a,b,c};
    }
    // Edge case: no clauses
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }
    
    // Build incidence lists for variables and clause literal signs
    vector<vector<pair<int,bool>>> varClauses(n+1); // (clause index, isPositive)
    vector<array<pair<int,bool>,3>> clauseLits(m); // per clause: (var, isPositive) for three lits
    vector<int> posCnt(n+1,0), negCnt(n+1,0);
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            int lit = clauses[i][j];
            int v = abs(lit);
            bool pos = lit > 0;
            clauseLits[i][j] = {v, pos};
            varClauses[v].push_back({i, pos});
            if (pos) posCnt[v]++; else negCnt[v]++;
        }
    }
    
    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> coin(0,1);
    uniform_int_distribution<int> noiseDist(0,99);
    
    auto now = [&](){ return chrono::steady_clock::now(); };
    auto startTime = now();
    const double TIME_LIMIT_MS = 1900.0; // roughly 1.9s
    auto elapsed_ms = [&](){
        return chrono::duration_cast<chrono::milliseconds>(now() - startTime).count();
    };
    
    // Best assignment across restarts
    vector<char> bestAssign(n+1, 0);
    int bestSatisfied = -1;
    
    // Prepare containers reused per restart
    vector<char> assign(n+1, 0);
    vector<int> cntTrue(m, 0);
    vector<int> posUnsat(m, -1);
    vector<int> unsatList;
    
    auto initialize = [&](bool heuristic){
        // assignment
        if (heuristic) {
            for (int v = 1; v <= n; ++v) {
                assign[v] = (posCnt[v] >= negCnt[v]) ? 1 : 0;
            }
        } else {
            for (int v = 1; v <= n; ++v) {
                assign[v] = coin(rng);
            }
        }
        // compute clause true counts
        int satisfied = 0;
        fill(cntTrue.begin(), cntTrue.end(), 0);
        fill(posUnsat.begin(), posUnsat.end(), -1);
        unsatList.clear();
        for (int i = 0; i < m; ++i) {
            int t = 0;
            for (int j = 0; j < 3; ++j) {
                int v = clauseLits[i][j].first;
                bool pos = clauseLits[i][j].second;
                bool litTrue = pos ? (assign[v] != 0) : (assign[v] == 0);
                if (litTrue) ++t;
            }
            cntTrue[i] = t;
            if (t == 0) {
                posUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            } else {
                satisfied++;
            }
        }
        return satisfied;
    };
    
    auto flipVar = [&](int v, int &satisfied){
        // flip variable v and update cntTrue, unsat list, satisfied
        assign[v] ^= 1;
        for (auto &pr : varClauses[v]) {
            int ci = pr.first;
            bool pos = pr.second;
            bool litTrueBefore = pos ? ((assign[v]^1) != 0) : ((assign[v]^1) == 0); // since assign[v] already flipped
            int before = cntTrue[ci];
            int delta = litTrueBefore ? -1 : +1; // after flip relative to before-flip
            int after = before + delta;
            if (before == 0 && after > 0) {
                satisfied++;
                // remove from unsat
                int p = posUnsat[ci];
                if (p != -1) {
                    int last = unsatList.back();
                    unsatList[p] = last;
                    posUnsat[last] = p;
                    unsatList.pop_back();
                    posUnsat[ci] = -1;
                }
            } else if (before > 0 && after == 0) {
                satisfied--;
                // add to unsat
                posUnsat[ci] = (int)unsatList.size();
                unsatList.push_back(ci);
            }
            cntTrue[ci] = after;
        }
    };
    
    auto gainOfVar = [&](int v)->int{
        int gain = 0;
        for (auto &pr : varClauses[v]) {
            int ci = pr.first;
            bool pos = pr.second;
            bool litTrue = pos ? (assign[v] != 0) : (assign[v] == 0);
            int k = cntTrue[ci];
            if (!litTrue) {
                // delta +1
                if (k == 0) gain += 1;
            } else {
                // delta -1
                if (k == 1) gain -= 1;
            }
        }
        return gain;
    };
    
    // Main loop with restarts
    bool first = true;
    while (elapsed_ms() < TIME_LIMIT_MS) {
        int satisfied = initialize(first); // first restart uses heuristic
        first = false;
        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestAssign = assign;
            if (bestSatisfied == m) break;
        }
        int maxSteps = max(200000, m * 30);
        for (int step = 0; step < maxSteps; ++step) {
            if (unsatList.empty()) {
                // all satisfied
                if (satisfied > bestSatisfied) {
                    bestSatisfied = satisfied;
                    bestAssign = assign;
                }
                break;
            }
            if (elapsed_ms() >= TIME_LIMIT_MS) break;
            // Pick a random unsatisfied clause
            int ci = unsatList[rng() % unsatList.size()];
            // Choose a var to flip in this clause
            int bestVar = -1;
            int bestGain = INT_MIN;
            int candVars[3];
            for (int j = 0; j < 3; ++j) candVars[j] = clauseLits[ci][j].first;
            // With some noise, choose random literal
            bool doNoise = noiseDist(rng) < 30; // 30% noise
            if (!doNoise) {
                for (int j = 0; j < 3; ++j) {
                    int v = candVars[j];
                    int g = gainOfVar(v);
                    if (g > bestGain || (g == bestGain && (rng() & 1))) {
                        bestGain = g;
                        bestVar = v;
                    }
                }
            } else {
                bestVar = candVars[rng() % 3];
            }
            if (bestVar == -1) bestVar = candVars[0];
            flipVar(bestVar, satisfied);
            if (satisfied > bestSatisfied) {
                bestSatisfied = satisfied;
                bestAssign = assign;
                if (bestSatisfied == m) break;
            }
        }
    }
    
    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << int(bestAssign[i]);
    }
    cout << '\n';
    return 0;
}