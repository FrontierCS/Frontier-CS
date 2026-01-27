#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v1, v2;
    uint8_t s1, s2; // true for positive literal, false for negated
};

static inline uint8_t litVal(const Clause& C, int which, const vector<uint8_t>& assign) {
    if (which == 0) return assign[C.v1] == C.s1;
    else return assign[C.v2] == C.s2;
}

static inline uint8_t clauseSat(const Clause& C, const vector<uint8_t>& assign) {
    return (assign[C.v1] == C.s1) | (assign[C.v2] == C.s2);
}

static inline void contribForVarInClause(int w, const Clause& C, const vector<uint8_t>& assign, uint8_t& make, uint8_t& brk) {
    make = 0; brk = 0;
    if (C.v1 == w && C.v2 == w) {
        uint8_t t1 = (assign[w] == C.s1);
        uint8_t t2 = (assign[w] == C.s2);
        if ((t1 | t2) == 0) {
            make = 1; // becomes satisfied after flip
        } else if (t1 == 1 && t2 == 1) {
            brk = 1; // becomes unsatisfied after flip
        }
    } else if (C.v1 == w) {
        uint8_t t_self = (assign[w] == C.s1);
        uint8_t t_other = (assign[C.v2] == C.s2);
        if (!t_other) {
            if (t_self) brk = 1;
            else make = 1;
        }
    } else if (C.v2 == w) {
        uint8_t t_self = (assign[w] == C.s2);
        uint8_t t_other = (assign[C.v1] == C.s1);
        if (!t_other) {
            if (t_self) brk = 1;
            else make = 1;
        }
    }
}

// 2-SAT solver using Kosaraju
bool two_sat(int n, const vector<Clause>& clauses, vector<uint8_t>& out_assign) {
    int N = 2 * n;
    vector<vector<int>> g(N), gr(N);
    auto idx = [&](int v, bool sign) { return 2 * (v - 1) + (sign ? 0 : 1); }; // pos -> 0, neg -> 1
    auto addImp = [&](int u, int v) { g[u].push_back(v); gr[v].push_back(u); };
    for (const auto& C : clauses) {
        int a = idx(C.v1, C.s1);
        int nota = a ^ 1;
        int b = idx(C.v2, C.s2);
        int notb = b ^ 1;
        addImp(nota, b);
        addImp(notb, a);
    }
    vector<int> order, comp(N, -1), vis(N, 0);
    order.reserve(N);
    function<void(int)> dfs1 = [&](int v) {
        vis[v] = 1;
        for (int to : g[v]) if (!vis[to]) dfs1(to);
        order.push_back(v);
    };
    function<void(int,int)> dfs2 = [&](int v, int c) {
        comp[v] = c;
        for (int to : gr[v]) if (comp[to] == -1) dfs2(to, c);
    };
    for (int i = 0; i < N; ++i) if (!vis[i]) dfs1(i);
    int j = 0;
    for (int i = N - 1; i >= 0; --i) {
        int v = order[i];
        if (comp[v] == -1) dfs2(v, j++);
    }
    out_assign.assign(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        int p = 2 * (v - 1);
        if (comp[p] == comp[p ^ 1]) {
            return false;
        }
        out_assign[v] = comp[p] > comp[p ^ 1] ? 1 : 0; // if pos component > neg component
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses;
    clauses.reserve(m);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        int va = abs(a), vb = abs(b);
        uint8_t sa = a > 0, sb = b > 0;
        clauses.push_back({va, vb, sa, sb});
        if (sa) posCnt[va]++; else negCnt[va]++;
        if (sb) posCnt[vb]++; else negCnt[vb]++;
    }

    // Trivial case
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // Try exact 2-SAT (if satisfiable)
    vector<uint8_t> assign2;
    if (two_sat(n, clauses, assign2)) {
        for (int i = 1; i <= n; ++i) {
            cout << int(assign2[i]) << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // Local search (Max-2-SAT)
    // Build adjacency: for each variable, list clause indices (no duplication for double occurrence)
    vector<vector<int>> adj(n + 1);
    adj.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        const Clause& C = clauses[i];
        if (C.v1 == C.v2) {
            adj[C.v1].push_back(i);
        } else {
            adj[C.v1].push_back(i);
            adj[C.v2].push_back(i);
        }
    }

    // Timing
    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.8; // seconds

    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Helper structures
    vector<uint8_t> assign(n + 1, 0);
    vector<uint8_t> bestAssign(n + 1, 0);
    int bestSat = -1;

    auto elapsed = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double>(now - start_time).count();
    };

    auto init_assignment_majority = [&]() {
        for (int v = 1; v <= n; ++v) {
            if (posCnt[v] > negCnt[v]) assign[v] = 1;
            else if (posCnt[v] < negCnt[v]) assign[v] = 0;
            else assign[v] = (rng() & 1);
        }
    };

    auto random_assignment = [&]() {
        for (int v = 1; v <= n; ++v) assign[v] = (rng() & 1);
    };

    // Run multiple restarts until time limit
    vector<uint8_t> sat(m, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList;
    vector<int> makeCount(n + 1, 0), breakCount(n + 1, 0);

    struct Rec {
        int cid;
        int u;
        uint8_t bmv, bbv, bmu, bbu, satBefore;
    };

    auto compute_initial = [&](int& satisfiedCount) {
        // sat and unsat
        satisfiedCount = 0;
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            sat[i] = clauseSat(clauses[i], assign);
            if (sat[i]) satisfiedCount++;
            else {
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            }
        }
        // make/break
        fill(makeCount.begin(), makeCount.end(), 0);
        fill(breakCount.begin(), breakCount.end(), 0);
        for (int v = 1; v <= n; ++v) {
            for (int cid : adj[v]) {
                const Clause& C = clauses[cid];
                if (C.v1 == v && C.v2 == v) {
                    uint8_t t1 = (assign[v] == C.s1);
                    uint8_t t2 = (assign[v] == C.s2);
                    if ((t1 | t2) == 0) makeCount[v]++;
                    else if (t1 == 1 && t2 == 1) breakCount[v]++;
                } else if (C.v1 == v) {
                    uint8_t t_other = (assign[C.v2] == C.s2);
                    uint8_t t_self = (assign[v] == C.s1);
                    if (!t_other) {
                        if (t_self) breakCount[v]++;
                        else makeCount[v]++;
                    }
                } else if (C.v2 == v) {
                    uint8_t t_other = (assign[C.v1] == C.s1);
                    uint8_t t_self = (assign[v] == C.s2);
                    if (!t_other) {
                        if (t_self) breakCount[v]++;
                        else makeCount[v]++;
                    }
                }
            }
        }
    };

    auto addUnsat = [&](int cid) {
        if (posInUnsat[cid] == -1) {
            posInUnsat[cid] = (int)unsatList.size();
            unsatList.push_back(cid);
        }
    };
    auto removeUnsat = [&](int cid) {
        int pos = posInUnsat[cid];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        posInUnsat[last] = pos;
        unsatList.pop_back();
        posInUnsat[cid] = -1;
    };

    auto flipVar = [&](int v, int& satisfiedCount) {
        vector<Rec> recs;
        recs.reserve(adj[v].size());
        // First pass: record before contributions and sat
        for (int cid : adj[v]) {
            const Clause& C = clauses[cid];
            Rec r;
            r.cid = cid;
            if (C.v1 == v && C.v2 == v) r.u = -1;
            else r.u = (C.v1 == v ? C.v2 : C.v1);
            r.satBefore = sat[cid];
            contribForVarInClause(v, C, assign, r.bmv, r.bbv);
            if (r.u != -1) contribForVarInClause(r.u, C, assign, r.bmu, r.bbu);
            else { r.bmu = 0; r.bbu = 0; }
            recs.push_back(r);
        }
        // Flip variable
        assign[v] ^= 1u;
        // Second pass: update make/break counts and satisfied/unsatisfied sets
        for (const Rec& r : recs) {
            const Clause& C = clauses[r.cid];
            uint8_t amv, abv;
            contribForVarInClause(v, C, assign, amv, abv);
            makeCount[v] += int(amv) - int(r.bmv);
            breakCount[v] += int(abv) - int(r.bbv);
            if (r.u != -1) {
                uint8_t amu, abu;
                contribForVarInClause(r.u, C, assign, amu, abu);
                makeCount[r.u] += int(amu) - int(r.bmu);
                breakCount[r.u] += int(abu) - int(r.bbu);
            }
            uint8_t afterSat = clauseSat(C, assign);
            if (afterSat != r.satBefore) {
                if (afterSat) {
                    satisfiedCount++;
                    removeUnsat(r.cid);
                } else {
                    satisfiedCount--;
                    addUnsat(r.cid);
                }
                sat[r.cid] = afterSat;
            }
        }
    };

    double noise = 0.3;
    int tries = 0;
    while (elapsed() < TIME_LIMIT) {
        int satisfiedCount = 0;
        if (tries == 0) init_assignment_majority();
        else random_assignment();
        compute_initial(satisfiedCount);

        // Track best
        if (satisfiedCount > bestSat) {
            bestSat = satisfiedCount;
            bestAssign = assign;
            if (bestSat == m) break;
        }

        // WalkSAT-like local search
        while (elapsed() < TIME_LIMIT) {
            if (unsatList.empty()) {
                // Found satisfying assignment (shouldn't happen since 2SAT reported unsat, but keep anyway)
                if (satisfiedCount > bestSat) {
                    bestSat = satisfiedCount;
                    bestAssign = assign;
                }
                break;
            }
            int cid = unsatList[rng() % unsatList.size()];
            const Clause& C = clauses[cid];
            int v1 = C.v1, v2 = C.v2;
            int chosenVar;
            if (v1 == v2) {
                chosenVar = v1;
            } else {
                bool doRandom = (rng() % 1000) < int(noise * 1000.0);
                if (doRandom) {
                    chosenVar = (rng() & 1) ? v1 : v2;
                } else {
                    int delta1 = makeCount[v1] - breakCount[v1];
                    int delta2 = makeCount[v2] - breakCount[v2];
                    if (delta1 > delta2) chosenVar = v1;
                    else if (delta2 > delta1) chosenVar = v2;
                    else chosenVar = (rng() & 1) ? v1 : v2;
                }
            }

            flipVar(chosenVar, satisfiedCount);

            if (satisfiedCount > bestSat) {
                bestSat = satisfiedCount;
                bestAssign = assign;
                if (bestSat == m) break;
            }
        }
        if (bestSat == m) break;
        tries++;
    }

    for (int i = 1; i <= n; ++i) {
        cout << int(bestAssign[i]) << (i == n ? '\n' : ' ');
    }
    return 0;
}