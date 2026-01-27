#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int var[3];       // variable indices 0..n-1
    uint8_t sign[3];  // 1 if positive, 0 if negated
    uint8_t trueCount; // number of true literals under current assignment
};

struct Solver {
    int n, m;
    vector<Clause> clauses;
    vector<vector<int>> occ; // occ[v] = list of clause ids where variable v appears (unique)
    vector<int> posCount, negCount;

    vector<int> breakCount;  // for each variable: number of clauses that would become unsatisfied if flipped
    vector<int> unsatList;   // indices of unsatisfied clauses
    vector<int> posInUnsat;  // position of each clause in unsatList or -1
    vector<char> assign;     // current assignment: 0/1

    mt19937_64 rng;
    const int PROB_SCALE = 1000000;
    int noiseP = 400000; // 0.4

    Solver(int n_, int m_) : n(n_), m(m_), clauses(m_), occ(n_), posCount(n_,0), negCount(n_,0), rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count()) {}

    inline bool litTrue(int clauseIdx, int j, const vector<char>& asg) const {
        const Clause &cl = clauses[clauseIdx];
        int v = cl.var[j];
        bool val = asg[v];
        return cl.sign[j] ? val : !val;
    }

    inline void addUnsat(int cid) {
        if (posInUnsat[cid] == -1) {
            posInUnsat[cid] = (int)unsatList.size();
            unsatList.push_back(cid);
        }
    }

    inline void removeUnsat(int cid) {
        int pos = posInUnsat[cid];
        if (pos == -1) return;
        int lastCid = unsatList.back();
        unsatList[pos] = lastCid;
        posInUnsat[lastCid] = pos;
        unsatList.pop_back();
        posInUnsat[cid] = -1;
    }

    void buildOccurrences() {
        vector<vector<int>> occRaw(n);
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < 3; ++j) {
                occRaw[clauses[i].var[j]].push_back(i);
            }
        }
        for (int v = 0; v < n; ++v) {
            auto &vec = occRaw[v];
            sort(vec.begin(), vec.end());
            vec.erase(unique(vec.begin(), vec.end()), vec.end());
            occ[v] = move(vec);
        }
    }

    void initAssignmentMajority(vector<char>& asg) {
        asg.assign(n, 0);
        for (int i = 0; i < n; ++i) {
            if (posCount[i] > negCount[i]) asg[i] = 1;
            else if (posCount[i] < negCount[i]) asg[i] = 0;
            else asg[i] = (rng() & 1);
        }
    }

    void initAssignmentRandom(vector<char>& asg) {
        asg.assign(n, 0);
        for (int i = 0; i < n; ++i) asg[i] = (rng() & 1);
    }

    void computeInitial(const vector<char>& initAsg) {
        assign = initAsg;
        breakCount.assign(n, 0);
        unsatList.clear();
        posInUnsat.assign(m, -1);
        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            int uniqVar = -1;
            for (int j = 0; j < 3; ++j) {
                int v = clauses[i].var[j];
                bool lit = clauses[i].sign[j] ? (bool)assign[v] : !assign[v];
                if (lit) { cnt++; uniqVar = v; }
            }
            clauses[i].trueCount = (uint8_t)cnt;
            if (cnt == 0) addUnsat(i);
            else if (cnt == 1 && uniqVar != -1) breakCount[uniqVar]++;
        }
    }

    // Flip variable v and update structures
    void flipVar(int v) {
        bool oldVal = assign[v];
        assign[v] = !assign[v];

        for (int cid : occ[v]) {
            Clause &cl = clauses[cid];
            int tc_before = cl.trueCount;

            int uniqueBeforeVar = -1;
            if (tc_before == 1) {
                // find which literal was true before flip
                for (int j = 0; j < 3; ++j) {
                    int w = cl.var[j];
                    bool val = (w == v) ? oldVal : (bool)assign[w];
                    bool lit = cl.sign[j] ? val : !val;
                    if (lit) { uniqueBeforeVar = w; break; }
                }
            }

            // After flip
            int tc_after = 0;
            int uniqueAfterVar = -1;
            for (int j = 0; j < 3; ++j) {
                int w = cl.var[j];
                bool val = (bool)assign[w];
                bool lit = cl.sign[j] ? val : !val;
                if (lit) {
                    tc_after++;
                    uniqueAfterVar = w;
                }
            }

            if (tc_before == 0 && tc_after > 0) {
                removeUnsat(cid);
            } else if (tc_before > 0 && tc_after == 0) {
                addUnsat(cid);
            }

            if (tc_before == 1 && uniqueBeforeVar != -1) {
                breakCount[uniqueBeforeVar]--;
            }
            if (tc_after == 1 && uniqueAfterVar != -1) {
                breakCount[uniqueAfterVar]++;
            }

            cl.trueCount = (uint8_t)tc_after;
        }
    }

    int pickVarFromClause(int cid) {
        Clause &cl = clauses[cid];
        int cand[3];
        int csize = 0;
        // collect unique variables in the clause
        for (int j = 0; j < 3; ++j) {
            int v = cl.var[j];
            bool exists = false;
            for (int k = 0; k < csize; ++k) if (cand[k] == v) { exists = true; break; }
            if (!exists) cand[csize++] = v;
        }

        // If any zero-break variable exists, choose randomly among them
        int zeroIdx[3];
        int zc = 0;
        for (int i = 0; i < csize; ++i) {
            if (breakCount[cand[i]] == 0) zeroIdx[zc++] = i;
        }
        if (zc > 0) {
            int pick = zeroIdx[ (int)(rng() % zc) ];
            return cand[pick];
        }

        // With probability 'noise', pick random among candidates
        if ((int)(rng() % PROB_SCALE) < noiseP) {
            return cand[ (int)(rng() % csize) ];
        }

        // Otherwise pick minimal break
        int bestVar = cand[0];
        int bestBreak = breakCount[bestVar];
        for (int i = 1; i < csize; ++i) {
            int v = cand[i];
            int b = breakCount[v];
            if (b < bestBreak || (b == bestBreak && (rng() & 1))) {
                bestBreak = b;
                bestVar = v;
            }
        }
        return bestVar;
    }

    vector<char> solve(double timeLimitSec = 0.95) {
        buildOccurrences();

        vector<char> bestAssign(n, 0);
        vector<char> curInit(n, 0);
        initAssignmentMajority(curInit);
        computeInitial(curInit);

        int bestUnsat = (int)unsatList.size();
        bestAssign = assign;

        auto start = chrono::steady_clock::now();
        int restart = 0;
        const int timeCheckInterval = 1024;

        while (true) {
            // If time exceeded, stop
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed >= timeLimitSec) break;

            // Run local search from current assignment
            int steps = 0;
            while (!unsatList.empty()) {
                if ((steps & (timeCheckInterval - 1)) == 0) {
                    now = chrono::steady_clock::now();
                    elapsed = chrono::duration<double>(now - start).count();
                    if (elapsed >= timeLimitSec) break;
                }
                int cid = unsatList[ (int)(rng() % unsatList.size()) ];

                int v = pickVarFromClause(cid);
                flipVar(v);
                steps++;

                int curUnsat = (int)unsatList.size();
                if (curUnsat < bestUnsat) {
                    bestUnsat = curUnsat;
                    bestAssign = assign;
                    if (bestUnsat == 0) return bestAssign;
                }
            }

            // Prepare next restart
            restart++;
            // Initialize next starting assignment: alternate strategies
            if (restart % 3 == 1) {
                initAssignmentRandom(curInit);
            } else if (restart % 3 == 2) {
                // mutate best assignment slightly
                curInit = bestAssign;
                for (int i = 0; i < n; ++i) {
                    if ((rng() % 1000) < 30) { // ~3% mutate
                        curInit[i] = rng() & 1;
                    }
                }
            } else {
                initAssignmentMajority(curInit);
            }
            computeInitial(curInit);

            int curUnsat = (int)unsatList.size();
            if (curUnsat < bestUnsat) {
                bestUnsat = curUnsat;
                bestAssign = assign;
                if (bestUnsat == 0) return bestAssign;
            }
        }
        return bestAssign;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    Solver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lit[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int x = lit[j];
            int v = abs(x) - 1;
            solver.clauses[i].var[j] = v;
            solver.clauses[i].sign[j] = (x > 0) ? 1 : 0;
            if (x > 0) solver.posCount[v]++; else solver.negCount[v]++;
        }
        solver.clauses[i].trueCount = 0;
    }

    vector<char> result = solver.solve();
    for (int i = 0; i < n; ++i) {
        cout << (result[i] ? 1 : 0) << (i + 1 == n ? '\n' : ' ');
    }
    return 0;
}