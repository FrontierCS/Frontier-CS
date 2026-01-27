#include <bits/stdc++.h>
using namespace std;

static inline bool litTrue(int lit, const vector<uint8_t>& assign) {
    int v = abs(lit);
    bool val = assign[v];
    return lit > 0 ? val : !val;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<int> A(m), B(m), C(m);
    for (int i = 0; i < m; ++i) {
        cin >> A[i] >> B[i] >> C[i];
    }

    // If no clauses, output all zeros
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Build variable to clauses mapping (unique per clause)
    vector<vector<int>> varClauses(n + 1);
    vector<array<int,3>> clsLits(m);
    vector<vector<int>> clauseVarsUnique(m);
    for (int i = 0; i < m; ++i) {
        clsLits[i] = {A[i], B[i], C[i]};
        // unique vars for this clause
        bool seen[51] = {false};
        vector<int> uniq;
        for (int k = 0; k < 3; ++k) {
            int v = abs(clsLits[i][k]);
            if (!seen[v]) {
                seen[v] = true;
                uniq.push_back(v);
            }
        }
        clauseVarsUnique[i] = uniq;
        for (int v : uniq) varClauses[v].push_back(i);
    }

    auto truthCount = [&](int idx, const vector<uint8_t>& assign)->int {
        int cnt = 0;
        auto &L = clsLits[idx];
        cnt += litTrue(L[0], assign);
        cnt += litTrue(L[1], assign);
        cnt += litTrue(L[2], assign);
        return cnt;
    };
    auto truthCountAfterFlip = [&](int idx, int v, const vector<uint8_t>& assign)->int {
        int cnt = 0;
        auto &L = clsLits[idx];
        for (int k = 0; k < 3; ++k) {
            int lit = L[k];
            int var = abs(lit);
            bool val = assign[var];
            if (var == v) val = !val;
            bool t = (lit > 0 ? val : !val);
            cnt += t;
        }
        return cnt;
    };

    // Random engine
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto randBit = [&](){ return (uint32_t)rng() & 1; };
    uniform_real_distribution<double> prob01(0.0, 1.0);

    // Time limit
    auto start = chrono::steady_clock::now();
    auto time_limit = start + chrono::milliseconds(950);

    vector<uint8_t> bestAssign(n + 1, 0);
    int bestS = -1;

    // WalkSAT with restarts
    const double p = 0.5;
    while (chrono::steady_clock::now() < time_limit) {
        // Random init
        vector<uint8_t> assign(n + 1, 0);
        for (int i = 1; i <= n; ++i) assign[i] = randBit();

        vector<int> tcount(m, 0);
        vector<int> unsatClauses;
        unsatClauses.reserve(m);
        vector<int> posInUnsat(m, -1);

        int satisfied = 0;
        for (int i = 0; i < m; ++i) {
            int tc = truthCount(i, assign);
            tcount[i] = tc;
            if (tc == 0) {
                posInUnsat[i] = (int)unsatClauses.size();
                unsatClauses.push_back(i);
            } else {
                satisfied++;
            }
        }

        if (satisfied > bestS) {
            bestS = satisfied;
            bestAssign = assign;
            if (bestS == m) break;
        }

        int steps = 0;
        int maxStepsBeforeRestart = 20000;
        while (chrono::steady_clock::now() < time_limit) {
            if (unsatClauses.empty()) break;
            int ci = unsatClauses[rng() % unsatClauses.size()];
            // Choose variable to flip
            int chooseVar = 0;
            auto &vars = clauseVarsUnique[ci];
            if (vars.empty()) { // Should not happen, but safe guard
                // random variable
                chooseVar = 1 + (rng() % n);
            } else {
                if (prob01(rng) < p) {
                    chooseVar = vars[rng() % vars.size()];
                } else {
                    int bestVar = vars[0];
                    int bestDelta = INT_MIN;
                    for (int v : vars) {
                        int delta = 0;
                        for (int j : varClauses[v]) {
                            int before = (tcount[j] > 0) ? 1 : 0;
                            int after = (truthCountAfterFlip(j, v, assign) > 0) ? 1 : 0;
                            delta += (after - before);
                        }
                        if (delta > bestDelta || (delta == bestDelta && (rng() & 1))) {
                            bestDelta = delta;
                            bestVar = v;
                        }
                    }
                    chooseVar = bestVar;
                }
            }

            // Flip chooseVar
            int v = chooseVar;
            assign[v] ^= 1;

            // Update affected clauses
            for (int j : varClauses[v]) {
                int oldtc = tcount[j];
                int newtc = truthCountAfterFlip(j, v, assign);
                tcount[j] = newtc;
                if (oldtc == 0 && newtc > 0) {
                    // remove from unsat
                    int pos = posInUnsat[j];
                    if (pos != -1) {
                        int last = unsatClauses.back();
                        unsatClauses[pos] = last;
                        posInUnsat[last] = pos;
                        unsatClauses.pop_back();
                        posInUnsat[j] = -1;
                    }
                    satisfied++;
                } else if (oldtc > 0 && newtc == 0) {
                    // add to unsat
                    if (posInUnsat[j] == -1) {
                        posInUnsat[j] = (int)unsatClauses.size();
                        unsatClauses.push_back(j);
                    }
                    satisfied--;
                }
            }

            if (satisfied > bestS) {
                bestS = satisfied;
                bestAssign = assign;
                if (bestS == m) break;
            }

            steps++;
            if (steps >= maxStepsBeforeRestart) break; // restart
        }

        if (bestS == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}