#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    vector<Clause> clauses(m);
    vector<vector<int>> occ(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);
    
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i] = {a, b};
        occ[abs(a)].push_back(i);
        occ[abs(b)].push_back(i);
        if (a > 0) posCnt[a]++; else negCnt[-a]++;
        if (b > 0) posCnt[b]++; else negCnt[-b]++;
    }
    
    for (int v = 1; v <= n; ++v) {
        auto &vec = occ[v];
        sort(vec.begin(), vec.end());
        vec.erase(unique(vec.begin(), vec.end()), vec.end());
    }
    
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto rand01 = [&]() -> int { return (int)(rng() & 1u); };
    
    vector<char> val(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] > negCnt[v]) val[v] = 1;
        else if (posCnt[v] < negCnt[v]) val[v] = 0;
        else val[v] = rand01();
    }
    
    auto evalClause = [&](int i) -> bool {
        const Clause &cl = clauses[i];
        bool la = (cl.a > 0) ? (bool)val[cl.a] : !val[-cl.a];
        bool lb = (cl.b > 0) ? (bool)val[cl.b] : !val[-cl.b];
        return la || lb;
    };
    
    vector<char> sat(m, 0);
    vector<int> unsat;
    unsat.reserve(m);
    vector<int> posInUnsat(m, -1);
    int satisfied = 0;
    for (int i = 0; i < m; ++i) {
        bool si = evalClause(i);
        sat[i] = si;
        if (!si) {
            posInUnsat[i] = (int)unsat.size();
            unsat.push_back(i);
        } else {
            ++satisfied;
        }
    }
    
    vector<char> bestVal = val;
    int bestSatisfied = satisfied;
    
    if (m > 0) {
        auto computeDelta = [&](int v) -> int {
            int delta = 0;
            for (int j : occ[v]) {
                const Clause &cl = clauses[j];
                bool la = (cl.a > 0) ? (bool)val[cl.a] : !val[-cl.a];
                bool lb = (cl.b > 0) ? (bool)val[cl.b] : !val[-cl.b];
                bool sat0 = la || lb;
                bool la2 = la, lb2 = lb;
                if (abs(cl.a) == v) la2 = !la2;
                if (abs(cl.b) == v) lb2 = !lb2;
                bool sat1 = la2 || lb2;
                if (sat1 && !sat0) ++delta;
                else if (!sat1 && sat0) --delta;
            }
            return delta;
        };
        
        int maxSteps = min(1000000, 25 * m + 10000);
        const int noiseNumer = 2, noiseDenom = 10; // 0.2 probability
        
        for (int step = 0; step < maxSteps; ++step) {
            if (unsat.empty()) break;
            int idx = unsat[rng() % unsat.size()];
            const Clause &cl = clauses[idx];
            int x = abs(cl.a), y = abs(cl.b);
            
            int chooseVar;
            if ((int)(rng() % noiseDenom) < noiseNumer) {
                chooseVar = ((int)(rng() & 1u)) ? x : y;
            } else {
                int dx = computeDelta(x);
                int dy = computeDelta(y);
                if (dx > dy) chooseVar = x;
                else if (dy > dx) chooseVar = y;
                else chooseVar = ((int)(rng() & 1u)) ? x : y;
            }
            
            int v = chooseVar;
            val[v] ^= 1;
            for (int j : occ[v]) {
                bool newSat = evalClause(j);
                if ((char)newSat != sat[j]) {
                    if (newSat) {
                        ++satisfied;
                        sat[j] = 1;
                        if (posInUnsat[j] != -1) {
                            int p = posInUnsat[j];
                            int last = unsat.back();
                            unsat[p] = last;
                            posInUnsat[last] = p;
                            unsat.pop_back();
                            posInUnsat[j] = -1;
                        }
                    } else {
                        --satisfied;
                        sat[j] = 0;
                        if (posInUnsat[j] == -1) {
                            posInUnsat[j] = (int)unsat.size();
                            unsat.push_back(j);
                        }
                    }
                }
            }
            
            if (satisfied > bestSatisfied) {
                bestSatisfied = satisfied;
                bestVal = val;
                if (bestSatisfied == m) break;
            }
        }
        
        if (bestSatisfied > satisfied) {
            val = bestVal;
            satisfied = bestSatisfied;
        }
    }
    
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)val[i];
    }
    cout << '\n';
    return 0;
}