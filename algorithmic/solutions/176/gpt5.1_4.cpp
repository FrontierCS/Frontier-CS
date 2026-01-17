#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[3];
    bool neg[3];
};

// Global variables
int n, m;
vector<Clause> clauses;
vector<vector<int>> occ;      // occ[var] = list of clause indices where var appears (unique per clause)
vector<char> assignment;      // current assignment 0/1
vector<char> bestAssignment;  // best found assignment
vector<char> clauseSat;       // clauseSat[i] = 1 if clause i is satisfied
vector<int> unsatList;        // indices of unsatisfied clauses
vector<int> unsatPos;         // position of clause in unsatList, -1 if satisfied
int satCount = 0;
int bestSatCount = 0;

mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
uniform_real_distribution<double> dist01(0.0, 1.0);

int computeDelta(int var) {
    int satDiff = 0;
    bool oldVal = assignment[var];
    bool newVal = !oldVal;
    for (int ci : occ[var]) {
        bool oldSat = clauseSat[ci];
        const Clause &cl = clauses[ci];
        bool newSat = false;
        for (int t = 0; t < 3; ++t) {
            int v2 = cl.v[t];
            bool val2 = (v2 == var ? newVal : (assignment[v2] != 0));
            bool litVal = cl.neg[t] ? !val2 : val2;
            if (litVal) {
                newSat = true;
                break;
            }
        }
        if (!oldSat && newSat) ++satDiff;
        else if (oldSat && !newSat) --satDiff;
    }
    return satDiff;
}

void flipVariable(int var) {
    assignment[var] ^= 1; // toggle 0/1
    for (int ci : occ[var]) {
        bool oldSat = clauseSat[ci];
        Clause &cl = clauses[ci];
        bool newSat = false;
        for (int t = 0; t < 3; ++t) {
            int v2 = cl.v[t];
            bool val2 = (assignment[v2] != 0);
            bool litVal = cl.neg[t] ? !val2 : val2;
            if (litVal) {
                newSat = true;
                break;
            }
        }
        if (oldSat != newSat) {
            clauseSat[ci] = newSat;
            if (newSat) {
                // unsatisfied -> satisfied
                int posInList = unsatPos[ci];
                int lastClause = unsatList.back();
                unsatList[posInList] = lastClause;
                unsatPos[lastClause] = posInList;
                unsatList.pop_back();
                unsatPos[ci] = -1;
                ++satCount;
            } else {
                // satisfied -> unsatisfied
                unsatPos[ci] = (int)unsatList.size();
                unsatList.push_back(ci);
                --satCount;
            }
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> m)) {
        return 0;
    }

    clauses.resize(m);
    occ.assign(n + 1, {});
    unsatPos.assign(m, -1);

    // Read clauses and build occurrences with unique clause per variable
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int arr[3] = {a, b, c};
        for (int k = 0; k < 3; ++k) {
            int lit = arr[k];
            clauses[i].neg[k] = (lit < 0);
            clauses[i].v[k] = abs(lit);
        }
        int uv[3];
        int uvCount = 0;
        for (int k = 0; k < 3; ++k) {
            int var = abs(arr[k]);
            bool exists = false;
            for (int t = 0; t < uvCount; ++t) {
                if (uv[t] == var) {
                    exists = true;
                    break;
                }
            }
            if (!exists) uv[uvCount++] = var;
        }
        for (int t = 0; t < uvCount; ++t) {
            int var = uv[t];
            if (var >= 1 && var <= n)
                occ[var].push_back(i);
        }
    }

    // Initial random assignment
    assignment.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        assignment[i] = (char)(rng() & 1);
    }

    clauseSat.assign(m, 0);
    unsatList.clear();
    satCount = 0;

    // Evaluate initial clauses
    for (int i = 0; i < m; ++i) {
        const Clause &cl = clauses[i];
        bool sat = false;
        for (int k = 0; k < 3; ++k) {
            int var = cl.v[k];
            bool val = (assignment[var] != 0);
            bool litVal = cl.neg[k] ? !val : val;
            if (litVal) {
                sat = true;
                break;
            }
        }
        clauseSat[i] = sat;
        if (!sat) {
            unsatPos[i] = (int)unsatList.size();
            unsatList.push_back(i);
        } else {
            unsatPos[i] = -1;
            ++satCount;
        }
    }

    bestAssignment = assignment;
    bestSatCount = satCount;

    if (m > 0) {
        const double WALK_PROB = 0.3;
        int maxSteps = 300 * n;
        for (int step = 0; step < maxSteps && bestSatCount < m; ++step) {
            if (unsatList.empty()) break;

            int ci = unsatList[rng() % unsatList.size()];
            Clause &cl = clauses[ci];

            bool doRandomWalk = (dist01(rng) < WALK_PROB);
            int chosenVar;

            if (doRandomWalk) {
                int pos = rng() % 3;
                chosenVar = cl.v[pos];
            } else {
                int bestDelta = INT_MIN;
                int bestVars[3];
                int bestCnt = 0;
                for (int k = 0; k < 3; ++k) {
                    int v = cl.v[k];
                    int delta = computeDelta(v);
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        bestVars[0] = v;
                        bestCnt = 1;
                    } else if (delta == bestDelta) {
                        bestVars[bestCnt++] = v;
                    }
                }
                chosenVar = bestVars[rng() % bestCnt];
            }

            flipVariable(chosenVar);

            if (satCount > bestSatCount) {
                bestSatCount = satCount;
                bestAssignment = assignment;
                if (bestSatCount == m) break;
            }
        }
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        cout << (bestAssignment[i] ? 1 : 0);
        if (i < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}