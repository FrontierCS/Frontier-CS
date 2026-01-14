#include <bits/stdc++.h>
using namespace std;

struct RNG {
    uint64_t x;
    RNG() {
        x = chrono::steady_clock::now().time_since_epoch().count();
        if (x == 0) x = 1;
    }
    inline uint64_t next() {
        x ^= x << 7;
        x ^= x >> 9;
        return x;
    }
    inline int nextInt(int l, int r) {
        return l + (int)(next() % (uint64_t)(r - l + 1));
    }
    inline double nextDouble() {
        return (next() >> 11) * (1.0 / 9007199254740992.0); // 2^53
    }
};

struct Lit {
    int var;
    bool neg;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<Lit, 3>> clauses(m);
    vector<vector<int>> varClauses(n);

    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            int x;
            cin >> x;
            int v = abs(x) - 1;
            bool neg = x < 0;
            clauses[i][j] = {v, neg};
            if (v >= 0 && v < n) {
                varClauses[v].push_back(i);
            }
        }
    }

    // If no clauses, any assignment is optimal
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            cout << 0 << (i + 1 == n ? '\n' : ' ');
        }
        return 0;
    }

    RNG rng;

    vector<char> val(n, 0), bestVal(n, 0);
    vector<int> cntTrue(m);
    vector<int> breakCount(n);
    vector<int> posInUnsat(m);
    vector<int> unsat;
    vector<int> clauseStamp(m);

    const double TIME_LIMIT = 0.95;
    auto start = chrono::steady_clock::now();

    int bestSat = 0;
    bool globalStop = false;

    int restart = 0;
    while (!globalStop) {
        double elapsed = chrono::duration<double>(chrono::steady_clock::now() - start).count();
        if (elapsed > TIME_LIMIT) break;
        ++restart;

        // Random initial assignment
        for (int i = 0; i < n; ++i) {
            val[i] = (char)(rng.next() & 1u);
        }

        // Initialize structures
        fill(cntTrue.begin(), cntTrue.end(), 0);
        fill(breakCount.begin(), breakCount.end(), 0);
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        unsat.clear();
        fill(clauseStamp.begin(), clauseStamp.end(), 0);
        int stamp = 1;

        // Compute cntTrue and unsatisfied clauses
        for (int c = 0; c < m; ++c) {
            int cnt = 0;
            auto &cl = clauses[c];
            for (int j = 0; j < 3; ++j) {
                int v = cl[j].var;
                bool neg = cl[j].neg;
                char vv = val[v];
                bool lit = neg ? !vv : vv;
                if (lit) ++cnt;
            }
            cntTrue[c] = cnt;
            if (cnt == 0) {
                posInUnsat[c] = (int)unsat.size();
                unsat.push_back(c);
            }
        }

        // Compute initial breakCount
        for (int c = 0; c < m; ++c) {
            int cnt = cntTrue[c];
            if (cnt == 1) {
                auto &cl = clauses[c];
                for (int j = 0; j < 3; ++j) {
                    int v = cl[j].var;
                    bool neg = cl[j].neg;
                    char vv = val[v];
                    bool lit = neg ? !vv : vv;
                    if (lit) {
                        ++breakCount[v];
                        break;
                    }
                }
            }
        }

        int curSat = m - (int)unsat.size();
        if (curSat > bestSat) {
            bestSat = curSat;
            bestVal = val;
            if (bestSat == m) {
                globalStop = true;
                break;
            }
        }

        long long step = 0;
        const double P_NOISE = 0.3;

        while (true) {
            if ((step & 0x3FFLL) == 0) {
                double elapsed2 = chrono::duration<double>(chrono::steady_clock::now() - start).count();
                if (elapsed2 > TIME_LIMIT) {
                    globalStop = true;
                    break;
                }
            }

            if (unsat.empty()) {
                curSat = m;
                if (curSat > bestSat) {
                    bestSat = curSat;
                    bestVal = val;
                }
                globalStop = true;
                break;
            }

            // Choose a random unsatisfied clause
            int ucIndex = rng.nextInt(0, (int)unsat.size() - 1);
            int c = unsat[ucIndex];
            auto &cl = clauses[c];
            int vs[3] = {cl[0].var, cl[1].var, cl[2].var};

            // Choose variable to flip
            int chosenVar;
            double r = rng.nextDouble();
            if (r < P_NOISE) {
                int idx = rng.nextInt(0, 2);
                chosenVar = vs[idx];
            } else {
                int bestBreak = INT_MAX;
                int cand[3];
                int candSz = 0;
                for (int k = 0; k < 3; ++k) {
                    int v = vs[k];
                    int bc = breakCount[v];
                    if (bc < bestBreak) {
                        bestBreak = bc;
                        candSz = 0;
                        cand[candSz++] = v;
                    } else if (bc == bestBreak) {
                        cand[candSz++] = v;
                    }
                }
                chosenVar = cand[rng.nextInt(0, candSz - 1)];
            }

            // Flip the chosen variable
            int v = chosenVar;
            char oldVal = val[v];
            val[v] ^= 1;

            ++stamp;
            if (stamp == INT_MAX) {
                stamp = 1;
                fill(clauseStamp.begin(), clauseStamp.end(), 0);
            }

            for (int idx = 0; idx < (int)varClauses[v].size(); ++idx) {
                int cidx = varClauses[v][idx];
                if (clauseStamp[cidx] == stamp) continue;
                clauseStamp[cidx] = stamp;

                int oldCnt = cntTrue[cidx];
                auto &cl2 = clauses[cidx];

                // Remove old contributions to breakCount from this clause
                for (int j = 0; j < 3; ++j) {
                    int varX = cl2[j].var;
                    bool neg = cl2[j].neg;
                    char vb = (varX == v ? oldVal : val[varX]); // value before flip
                    bool litB = neg ? !vb : vb;
                    if (oldCnt == 1 && litB) {
                        --breakCount[varX];
                    }
                }

                // Compute new cntTrue
                int newCnt = 0;
                for (int j = 0; j < 3; ++j) {
                    int varX = cl2[j].var;
                    bool neg = cl2[j].neg;
                    char va = val[varX]; // after flip
                    bool litA = neg ? !va : va;
                    if (litA) ++newCnt;
                }

                bool oldSat = (oldCnt > 0);
                bool newSat = (newCnt > 0);
                cntTrue[cidx] = newCnt;

                if (oldSat && !newSat) {
                    // add to unsat
                    posInUnsat[cidx] = (int)unsat.size();
                    unsat.push_back(cidx);
                } else if (!oldSat && newSat) {
                    // remove from unsat
                    int pos = posInUnsat[cidx];
                    if (pos != -1) {
                        int lastClause = unsat.back();
                        unsat[pos] = lastClause;
                        posInUnsat[lastClause] = pos;
                        unsat.pop_back();
                        posInUnsat[cidx] = -1;
                    }
                }

                // Add new contributions from this clause
                for (int j = 0; j < 3; ++j) {
                    int varX = cl2[j].var;
                    bool neg = cl2[j].neg;
                    char va = val[varX];
                    bool litA = neg ? !va : va;
                    if (newCnt == 1 && litA) {
                        ++breakCount[varX];
                    }
                }
            }

            curSat = m - (int)unsat.size();
            if (curSat > bestSat) {
                bestSat = curSat;
                bestVal = val;
                if (bestSat == m) {
                    globalStop = true;
                    break;
                }
            }

            ++step;
        }

        if (globalStop) break;
    }

    for (int i = 0; i < n; ++i) {
        cout << (int)bestVal[i] << (i + 1 == n ? '\n' : ' ');
    }

    return 0;
}