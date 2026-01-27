#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v[3];           // variable indices 0..n-1
    unsigned char s[3]; // sign: 1 for positive, 0 for negative
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<pair<int,int>>> occ(n); // for each variable, list of (clause, position)
    vector<int> posCnt(n,0), negCnt(n,0);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        if (!(cin >> a >> b >> c)) {
            a = b = c = 0;
        }
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            int var = abs(x) - 1;
            unsigned char sign = (x > 0) ? 1 : 0;
            clauses[i].v[j] = var;
            clauses[i].s[j] = sign;
            occ[var].push_back({i, j});
            if (sign) posCnt[var]++; else negCnt[var]++;
        }
    }

    // Edge case: m == 0, output any assignment (all zeros).
    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // State vectors
    vector<unsigned char> assign(n, 0), bestAssign(n, 0);
    vector<int> trueCnt(m, 0);
    vector<int> breakCnt(n, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);

    auto addUnsat = [&](int ci) {
        if (posInUnsat[ci] == -1) {
            posInUnsat[ci] = (int)unsatList.size();
            unsatList.push_back(ci);
        }
    };
    auto removeUnsat = [&](int ci) {
        int pos = posInUnsat[ci];
        if (pos != -1) {
            int last = unsatList.back();
            unsatList[pos] = last;
            posInUnsat[last] = pos;
            unsatList.pop_back();
            posInUnsat[ci] = -1;
        }
    };

    // Compute true count for each clause
    auto recomputeTrueCnt = [&]() {
        fill(trueCnt.begin(), trueCnt.end(), 0);
        for (int i = 0; i < m; ++i) {
            int t = 0;
            for (int j = 0; j < 3; ++j) {
                int var = clauses[i].v[j];
                unsigned char sgn = clauses[i].s[j];
                if (assign[var] == sgn) ++t;
            }
            trueCnt[i] = t;
        }
    };

    // Initialize unsatisfied list
    auto initUnsatList = [&]() {
        unsatList.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            if (trueCnt[i] == 0) addUnsat(i);
        }
    };

    // Compute initial break count for all variables, handling duplicates in clauses
    auto recomputeBreakCnt = [&]() {
        fill(breakCnt.begin(), breakCnt.end(), 0);
        for (int i = 0; i < m; ++i) {
            int t = trueCnt[i];
            if (t <= 0) continue;
            // Compute per-unique-variable occurrence and currently true count in clause i
            int uv[3], kOcc[3], kTrue[3];
            int k = 0;
            for (int j = 0; j < 3; ++j) {
                int u = clauses[i].v[j];
                int idx = -1;
                for (int q = 0; q < k; ++q) if (uv[q] == u) { idx = q; break; }
                if (idx == -1) {
                    idx = k;
                    uv[k] = u;
                    kOcc[k] = 0;
                    kTrue[k] = 0;
                    ++k;
                }
                ++kOcc[idx];
                if (assign[u] == clauses[i].s[j]) ++kTrue[idx];
            }
            for (int c = 0; c < k; ++c) {
                int deltaIfFlip = kOcc[c] - 2 * kTrue[c];
                if (t + deltaIfFlip == 0) {
                    breakCnt[uv[c]]++;
                }
            }
        }
    };

    // Flip variable v with general robust updates
    vector<int> clauseStamp(m, -1);
    int curStamp = 0;
    auto flipVar = [&](int v) {
        unsigned char oldVal = assign[v];
        unsigned char newVal = oldVal ^ 1;
        assign[v] = newVal;

        ++curStamp;
        if (curStamp == INT_MAX / 2) {
            // Reset stamps to avoid overflow
            fill(clauseStamp.begin(), clauseStamp.end(), -1);
            curStamp = 1;
        }

        // Process each unique clause containing v
        for (auto &op : occ[v]) {
            int ci = op.first;
            if (clauseStamp[ci] == curStamp) continue;
            clauseStamp[ci] = curStamp;

            int tBefore = trueCnt[ci];

            // Build per-unique-variable stats before flip
            int uv[3], kOcc[3], kTrueBefore[3], kTrueAfter[3];
            int k = 0;
            for (int j = 0; j < 3; ++j) {
                int u = clauses[ci].v[j];
                int idx = -1;
                for (int q = 0; q < k; ++q) if (uv[q] == u) { idx = q; break; }
                if (idx == -1) {
                    idx = k;
                    uv[k] = u;
                    kOcc[k] = 0;
                    kTrueBefore[k] = 0;
                    ++k;
                }
                ++kOcc[idx];
                unsigned char valU = (u == v ? oldVal : assign[u]);
                if (valU == clauses[ci].s[j]) ++kTrueBefore[idx];
            }

            // Compute tAfter using v's stats
            int idxV = -1;
            for (int q = 0; q < k; ++q) if (uv[q] == v) { idxV = q; break; }
            int tAfter = tBefore;
            if (idxV != -1) {
                int delta = kOcc[idxV] - 2 * kTrueBefore[idxV];
                tAfter += delta;
            }
            // Prepare kTrueAfter
            for (int q = 0; q < k; ++q) {
                if (uv[q] == v) {
                    kTrueAfter[q] = kOcc[q] - kTrueBefore[q];
                } else {
                    kTrueAfter[q] = kTrueBefore[q];
                }
            }

            // Update break counts for variables appearing in this clause
            bool wasSat = (tBefore > 0);
            bool nowSat = (tAfter > 0);
            for (int q = 0; q < k; ++q) {
                int u = uv[q];
                int deltaBeforeIfFlipU = kOcc[q] - 2 * kTrueBefore[q];
                int deltaAfterIfFlipU  = kOcc[q] - 2 * kTrueAfter[q];
                bool wasBreak = wasSat && (tBefore + deltaBeforeIfFlipU == 0);
                bool nowBreak = nowSat && (tAfter + deltaAfterIfFlipU == 0);
                if (wasBreak != nowBreak) {
                    if (wasBreak) breakCnt[u]--;
                    else breakCnt[u]++;
                }
            }

            // Update trueCnt and unsatList
            if (tBefore == 0 && tAfter > 0) {
                removeUnsat(ci);
            } else if (tBefore > 0 && tAfter == 0) {
                addUnsat(ci);
            }
            trueCnt[ci] = tAfter;
        }
    };

    auto computeSatisfied = [&]() {
        return m - (int)unsatList.size();
    };

    // Initialize assignment
    auto initAssignment = [&](int mode) {
        // mode: 0 random, 1 majority with small random noise
        if (mode == 1) {
            for (int i = 0; i < n; ++i) {
                if (posCnt[i] > negCnt[i]) assign[i] = 1;
                else if (posCnt[i] < negCnt[i]) assign[i] = 0;
                else assign[i] = (rng() & 1) ? 1 : 0;
            }
            // Add some noise
            for (int i = 0; i < n; ++i) {
                if ((rng() & 1023) < 64) assign[i] ^= 1; // ~6.25% flip
            }
        } else {
            for (int i = 0; i < n; ++i) {
                assign[i] = (rng() & 1) ? 1 : 0;
            }
        }
        recomputeTrueCnt();
        initUnsatList();
        recomputeBreakCnt();
    };

    // WalkSAT parameters
    const double noiseProb = 0.40;

    // Time budget
    const int TIME_MS = 900; // adjust to be safe
    auto startTime = chrono::steady_clock::now();
    auto deadline = startTime + chrono::milliseconds(TIME_MS);

    int bestUnsat = m + 1;
    // At least initialize bestAssign to some simple assignment (majority), then refine
    initAssignment(1);
    bestAssign = assign;
    bestUnsat = (int)unsatList.size();

    int restartCount = 0;
    while (chrono::steady_clock::now() < deadline) {
        // Alternate initialization modes
        int mode = (restartCount % 2 == 0) ? 1 : 0;
        initAssignment(mode);

        int currentUnsat = (int)unsatList.size();
        if (currentUnsat < bestUnsat) {
            bestUnsat = currentUnsat;
            bestAssign = assign;
            if (bestUnsat == 0) break;
        }

        // Local search with restarts
        int stepsSinceImprovement = 0;
        int lastImprovementUnsat = currentUnsat;
        // Set a dynamic stall limit depending on m
        int stallLimit = max(2000, 20 * m + 1000);
        while (chrono::steady_clock::now() < deadline) {
            if (unsatList.empty()) {
                // Found a satisfying assignment
                bestAssign = assign;
                bestUnsat = 0;
                break;
            }
            // Choose random unsatisfied clause
            int idx = (int)(rng() % unsatList.size());
            int ci = unsatList[idx];

            // Determine candidate variables (unique variables in ci)
            int uv[3], k = 0;
            for (int j = 0; j < 3; ++j) {
                int u = clauses[ci].v[j];
                bool exists = false;
                for (int t = 0; t < k; ++t) if (uv[t] == u) { exists = true; break; }
                if (!exists) uv[k++] = u;
            }

            // Among candidates, pick based on break counts
            int chosenVar = uv[0];
            // Check zero-break candidates
            vector<int> zeroBreak;
            zeroBreak.reserve(3);
            for (int t = 0; t < k; ++t) {
                int u = uv[t];
                if (breakCnt[u] == 0) zeroBreak.push_back(u);
            }
            uniform_real_distribution<double> real01(0.0, 1.0);
            if (!zeroBreak.empty()) {
                chosenVar = zeroBreak[(int)(rng() % zeroBreak.size())];
            } else {
                if (real01(rng) < noiseProb) {
                    chosenVar = uv[(int)(rng() % k)];
                } else {
                    int bestBC = INT_MAX;
                    for (int t = 0; t < k; ++t) {
                        int u = uv[t];
                        if (breakCnt[u] < bestBC) {
                            bestBC = breakCnt[u];
                            chosenVar = u;
                        }
                    }
                }
            }

            int beforeUnsat = (int)unsatList.size();
            flipVar(chosenVar);
            int afterUnsat = (int)unsatList.size();

            if (afterUnsat < bestUnsat) {
                bestUnsat = afterUnsat;
                bestAssign = assign;
                lastImprovementUnsat = afterUnsat;
                stepsSinceImprovement = 0;
                if (bestUnsat == 0) break;
            } else {
                if (afterUnsat < beforeUnsat) {
                    lastImprovementUnsat = afterUnsat;
                    stepsSinceImprovement = 0;
                } else {
                    stepsSinceImprovement++;
                }
            }

            if (stepsSinceImprovement > stallLimit) break; // restart
        }

        if (bestUnsat == 0) break;
        restartCount++;
    }

    // Output best assignment found
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';
    return 0;
}