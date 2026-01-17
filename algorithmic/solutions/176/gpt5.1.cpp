#include <bits/stdc++.h>
using namespace std;

struct Occ {
    int clause;
    uint8_t pos;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int, 3>> clauses(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i][0] >> clauses[i][1] >> clauses[i][2];
    }

    if (m == 0) {
        // Any assignment is fine; output all 0
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Build occurrences list
    vector<vector<Occ>> occ(n + 1);
    for (int ci = 0; ci < m; ++ci) {
        for (int k = 0; k < 3; ++k) {
            int lit = clauses[ci][k];
            int v = abs(lit);
            occ[v].push_back({ci, (uint8_t)k});
        }
    }

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    vector<uint8_t> clauseTrueCnt(m);
    vector<int> posInUnsat(m);
    vector<int> unsatClauses;
    vector<uint8_t> val(n + 1);       // current assignment: 0/1
    vector<uint8_t> bestVal(n + 1);   // best assignment found

    int bestSat = -1;
    int totalClauses = m;

    // For break count computation with possible duplicate literals
    vector<int> seen(m, 0);
    int seenStamp = 1;

    auto compute_break_count = [&](int v) -> int {
        int stamp = seenStamp++;
        vector<int> visited;
        visited.reserve(occ[v].size());

        for (const auto &o : occ[v]) {
            int ci = o.clause;
            if (seen[ci] != stamp) {
                seen[ci] = stamp;
                visited.push_back(ci);
            }
        }

        int bc = 0;
        bool vCur = val[v];

        for (int ci : visited) {
            int Tbefore = clauseTrueCnt[ci];
            int Tafter = Tbefore;
            // adjust Tafter for each occurrence of v in this clause
            for (int k = 0; k < 3; ++k) {
                int lit = clauses[ci][k];
                if (abs(lit) == v) {
                    bool litBefore = (lit > 0) ? vCur : !vCur;
                    if (litBefore) Tafter--;
                    else Tafter++;
                }
            }
            if (Tbefore > 0 && Tafter == 0) bc++;
        }
        return bc;
    };

    const int MAX_TRIES = 30;
    const int MAX_FLIPS = 10000;
    const int WALK_PROB_NUM = 40;  // 0.4 probability
    const int WALK_PROB_DEN = 100;

    bool done = false;

    for (int t = 0; t < MAX_TRIES && !done; ++t) {
        // Random initial assignment
        for (int i = 1; i <= n; ++i) {
            val[i] = (uint8_t)(rng() & 1);
        }

        // Initialize clause truth counts and unsatisfied list
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        unsatClauses.clear();
        int curSat = 0;

        for (int ci = 0; ci < m; ++ci) {
            int T = 0;
            for (int k = 0; k < 3; ++k) {
                int lit = clauses[ci][k];
                int v = abs(lit);
                bool litTrue = (lit > 0) ? (bool)val[v] : !(bool)val[v];
                if (litTrue) ++T;
            }
            clauseTrueCnt[ci] = (uint8_t)T;
            if (T == 0) {
                posInUnsat[ci] = (int)unsatClauses.size();
                unsatClauses.push_back(ci);
            } else {
                ++curSat;
            }
        }

        if (curSat > bestSat) {
            bestSat = curSat;
            bestVal = val;
            if (bestSat == totalClauses) {
                done = true;
                break;
            }
        }

        for (int step = 0; step < MAX_FLIPS && !unsatClauses.empty() && !done; ++step) {
            // Pick a random unsatisfied clause
            int ci = unsatClauses[rng() % unsatClauses.size()];

            int vars[3];
            for (int k = 0; k < 3; ++k) vars[k] = abs(clauses[ci][k]);

            int bc[3];
            int zeroIdx[3];
            int zeroCount = 0;
            int minBc = INT_MAX;

            for (int k = 0; k < 3; ++k) {
                int v = vars[k];
                bc[k] = compute_break_count(v);
                if (bc[k] == 0) {
                    zeroIdx[zeroCount++] = k;
                }
                if (bc[k] < minBc) minBc = bc[k];
            }

            int chosenIdx;
            if (zeroCount > 0) {
                chosenIdx = zeroIdx[rng() % zeroCount];
            } else if ((int)(rng() % WALK_PROB_DEN) < WALK_PROB_NUM) {
                chosenIdx = (int)(rng() % 3);
            } else {
                int bestIdx[3];
                int bestCnt = 0;
                for (int k = 0; k < 3; ++k) {
                    if (bc[k] == minBc) bestIdx[bestCnt++] = k;
                }
                chosenIdx = bestIdx[rng() % bestCnt];
            }

            int v = vars[chosenIdx];
            bool oldVal = (bool)val[v];
            bool newVal = !oldVal;
            val[v] = (uint8_t)newVal;

            // Update all affected clauses
            for (const auto &o : occ[v]) {
                int cj = o.clause;
                int T = clauseTrueCnt[cj];
                int lit = clauses[cj][o.pos];

                bool litBefore = (lit > 0) ? oldVal : !oldVal;
                bool litAfter  = !litBefore;

                int Tnew = T;
                if (litBefore && !litAfter) --Tnew;
                else if (!litBefore && litAfter) ++Tnew;

                if (T == 0 && Tnew > 0) {
                    // unsatisfied -> satisfied
                    ++curSat;
                    int idx = posInUnsat[cj];
                    if (idx != -1) {
                        int lastClause = unsatClauses.back();
                        unsatClauses[idx] = lastClause;
                        posInUnsat[lastClause] = idx;
                        unsatClauses.pop_back();
                        posInUnsat[cj] = -1;
                    }
                } else if (T > 0 && Tnew == 0) {
                    // satisfied -> unsatisfied
                    --curSat;
                    if (posInUnsat[cj] == -1) {
                        posInUnsat[cj] = (int)unsatClauses.size();
                        unsatClauses.push_back(cj);
                    }
                }
                clauseTrueCnt[cj] = (uint8_t)Tnew;
            }

            if (curSat > bestSat) {
                bestSat = curSat;
                bestVal = val;
                if (bestSat == totalClauses) {
                    done = true;
                    break;
                }
            }
        }
    }

    // Output best assignment (1..n)
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';

    return 0;
}