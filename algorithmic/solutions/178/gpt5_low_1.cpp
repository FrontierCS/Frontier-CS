#include <bits/stdc++.h>
using namespace std;

struct Clause {
    array<int,3> var; // 0-based variable indices
    array<bool,3> pos; // true if positive literal
    int true_count = 0;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<int>> varClauses(n); // for each var, list of clause indices
    for (int i = 0; i < m; ++i) {
        int a,b,c;
        cin >> a >> b >> c;
        int lits[3] = {a,b,c};
        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            bool positive = x > 0;
            int v = abs(x) - 1;
            clauses[i].var[j] = v;
            clauses[i].pos[j] = positive;
            varClauses[v].push_back(i);
        }
    }

    auto now = [](){ return chrono::steady_clock::now(); };
    auto start = now();
    const double TIME_LIMIT_SEC = 0.95;

    mt19937 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t)&rng);

    auto literalTrue = [](int val, bool pos) {
        return pos ? (val == 1) : (val == 0);
    };

    vector<int> bestAssign(n, 0);
    int bestSat = (m==0?0: -1);

    // Data structures reused across restarts
    vector<int> assign(n);
    vector<int> make(n), brk(n);
    vector<int> unsatList;
    vector<int> unsatPos(m, -1);

    auto addUnsat = [&](int idx){
        if (unsatPos[idx] != -1) return;
        unsatPos[idx] = (int)unsatList.size();
        unsatList.push_back(idx);
    };
    auto removeUnsat = [&](int idx){
        int pos = unsatPos[idx];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        unsatPos[last] = pos;
        unsatList.pop_back();
        unsatPos[idx] = -1;
    };

    auto initialize = [&](){
        // random assignment
        for (int i = 0; i < n; ++i) assign[i] = rng() & 1;
        fill(make.begin(), make.end(), 0);
        fill(brk.begin(), brk.end(), 0);
        unsatList.clear();
        fill(unsatPos.begin(), unsatPos.end(), -1);

        for (int i = 0; i < m; ++i) {
            int tc = 0;
            int soleVar = -1;
            for (int j = 0; j < 3; ++j) {
                int v = clauses[i].var[j];
                bool pos = clauses[i].pos[j];
                if (literalTrue(assign[v], pos)) {
                    ++tc;
                    soleVar = v;
                }
            }
            clauses[i].true_count = tc;
            if (tc == 0) {
                addUnsat(i);
                // each var flip would satisfy this clause
                for (int j = 0; j < 3; ++j) {
                    make[clauses[i].var[j]]++;
                }
            } else if (tc == 1) {
                brk[soleVar]++;
            }
        }
    };

    auto recomputeSatisfied = [&]()->int{
        return m - (int)unsatList.size();
    };

    auto updateClauseCounts = [&](int cid, const vector<int>& assign_local, bool beforeUpdate, int &tc_cache, int &sole_before_or_after){
        // compute true_count for clause cid with current assign_local
        int tc = 0;
        int sole = -1;
        for (int k = 0; k < 3; ++k) {
            int v = clauses[cid].var[k];
            bool pos = clauses[cid].pos[k];
            if (literalTrue(assign_local[v], pos)) {
                tc++;
                sole = v;
            }
        }
        tc_cache = tc;
        sole_before_or_after = (tc==1 ? sole : -1);
    };

    auto flipVar = [&](int v){
        // Flip assignment[v], and update data structures
        assign[v] ^= 1;
        for (int cid : varClauses[v]) {
            int tc_before = clauses[cid].true_count;
            int sole_before = -1;
            if (tc_before == 1) {
                // find sole true var before
                for (int k = 0; k < 3; ++k) {
                    int u = clauses[cid].var[k];
                    bool pos = clauses[cid].pos[k];
                    if (literalTrue(assign[u] ^ 1, pos)) continue; // we flipped already, so this check is tricky
                }
            }
            // To avoid confusion due to already flipped assign[v], recompute tc_before by temporarily flipping back
            assign[v] ^= 1;
            int recomputed_before_tc = 0;
            int recomputed_before_sole = -1;
            for (int k = 0; k < 3; ++k) {
                int u = clauses[cid].var[k];
                bool pos = clauses[cid].pos[k];
                if (literalTrue(assign[u], pos)) {
                    recomputed_before_tc++;
                    recomputed_before_sole = u;
                }
            }
            assign[v] ^= 1;

            tc_before = recomputed_before_tc;
            sole_before = recomputed_before_sole;

            if (tc_before == 0) {
                // was unsatisfied, all three had make contribution
                for (int k = 0; k < 3; ++k) {
                    make[clauses[cid].var[k]]--;
                }
                removeUnsat(cid);
            } else if (tc_before == 1) {
                // sole true var loses a break
                brk[sole_before]--;
            }

            // compute after with current assignment (already flipped)
            int tc_after = 0;
            int sole_after = -1;
            for (int k = 0; k < 3; ++k) {
                int u = clauses[cid].var[k];
                bool pos = clauses[cid].pos[k];
                if (literalTrue(assign[u], pos)) {
                    tc_after++;
                    sole_after = u;
                }
            }

            if (tc_after == 0) {
                // becomes unsatisfied
                for (int k = 0; k < 3; ++k) {
                    make[clauses[cid].var[k]]++;
                }
                addUnsat(cid);
            } else if (tc_after == 1) {
                brk[sole_after]++;
            }

            clauses[cid].true_count = tc_after;
        }
    };

    auto improve = [&](){
        // run local search until time limit
        int currentBestSat = recomputeSatisfied();
        vector<int> currentBestAssign = assign;
        uniform_int_distribution<int> coin100(0, 99);
        int iter = 0;
        while (chrono::duration<double>(now() - start).count() < TIME_LIMIT_SEC) {
            if (unsatList.empty()) break;
            int cid = unsatList[rng() % unsatList.size()];
            // Choose variable to flip from this clause
            array<int,3> vs = clauses[cid].var;
            // Strategy: with some probability random, else pick max gain
            int chosen = -1;
            if (coin100(rng) < 20) {
                chosen = vs[rng() % 3];
            } else {
                int bestGain = INT_MIN;
                vector<int> candidates;
                for (int k = 0; k < 3; ++k) {
                    int v = vs[k];
                    int gain = make[v] - brk[v];
                    if (gain > bestGain) {
                        bestGain = gain;
                        candidates.clear();
                        candidates.push_back(v);
                    } else if (gain == bestGain) {
                        candidates.push_back(v);
                    }
                }
                chosen = candidates[rng() % candidates.size()];
            }
            flipVar(chosen);

            int satNow = m - (int)unsatList.size();
            if (satNow > currentBestSat) {
                currentBestSat = satNow;
                currentBestAssign = assign;
                if (satNow > bestSat) {
                    bestSat = satNow;
                    bestAssign = assign;
                    if (bestSat == m) break;
                }
            }

            // occasional random restart to escape local minima
            ++iter;
            if (iter % 10000 == 0) {
                if (coin100(rng) < 10) {
                    // restart
                    initialize();
                    currentBestSat = m - (int)unsatList.size();
                    currentBestAssign = assign;
                }
            }
        }
        // restore best found in this run
        assign = currentBestAssign;
        // Rebuild structures to be consistent with assign
        fill(make.begin(), make.end(), 0);
        fill(brk.begin(), brk.end(), 0);
        unsatList.clear();
        fill(unsatPos.begin(), unsatPos.end(), -1);
        for (int i = 0; i < m; ++i) {
            int tc = 0;
            int sole = -1;
            for (int k = 0; k < 3; ++k) {
                int v = clauses[i].var[k];
                bool pos = clauses[i].pos[k];
                if (literalTrue(assign[v], pos)) {
                    ++tc;
                    sole = v;
                }
            }
            clauses[i].true_count = tc;
            if (tc == 0) {
                addUnsat(i);
                for (int k = 0; k < 3; ++k) make[clauses[i].var[k]]++;
            } else if (tc == 1) {
                brk[sole]++;
            }
        }
        int satNow = m - (int)unsatList.size();
        if (satNow > bestSat) {
            bestSat = satNow;
            bestAssign = assign;
        }
    };

    if (m == 0) {
        // Any assignment works
        for (int i = 0; i < n; ++i) {
            cout << 0 << (i+1<n?' ':'\n');
        }
        return 0;
    }

    // Multiple restarts within time limit
    while (chrono::duration<double>(now() - start).count() < TIME_LIMIT_SEC) {
        initialize();
        int sat0 = m - (int)unsatList.size();
        if (sat0 > bestSat) {
            bestSat = sat0;
            bestAssign = assign;
            if (bestSat == m) break;
        }
        improve();
        if (bestSat == m) break;
    }

    for (int i = 0; i < n; ++i) {
        cout << bestAssign[i] << (i+1<n?' ':'\n');
    }
    return 0;
}