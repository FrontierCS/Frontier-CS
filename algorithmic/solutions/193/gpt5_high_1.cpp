#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<int> A(m), B(m);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i] = {a, b};
        A[i] = a; B[i] = b;
        if (a > 0) posCnt[a]++; else negCnt[-a]++;
        if (b > 0) posCnt[b]++; else negCnt[-b]++;
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

    // Build adjacency list: for each variable, list of clause indices it appears in (unique per clause)
    vector<vector<int>> adj(n + 1);
    adj.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int va = A[i] > 0 ? A[i] : -A[i];
        int vb = B[i] > 0 ? B[i] : -B[i];
        if (va == vb) {
            adj[va].push_back(i);
        } else {
            adj[va].push_back(i);
            adj[vb].push_back(i);
        }
    }

    // Random number generator
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);
    auto randInt = [&](int l, int r)->int {
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };
    auto randReal = [&]()->double {
        uniform_real_distribution<double> dist(0.0, 1.0);
        return dist(rng);
    };

    vector<char> assign(n + 1, 0), bestAssign(n + 1, 0);
    vector<char> sat(m, 0);
    vector<int> unsat;
    unsat.reserve(m);
    vector<int> posInUnsat(m, -1);

    auto litVal = [&](int lit)->bool {
        int v = lit > 0 ? lit : -lit;
        char val = assign[v];
        return lit > 0 ? (val != 0) : (val == 0);
    };

    auto clauseVal = [&](int idx)->bool {
        return litVal(A[idx]) || litVal(B[idx]);
    };

    auto clauseValAfterFlip = [&](int idx, int v)->bool {
        int la = A[idx], lb = B[idx];
        int va = la > 0 ? la : -la;
        int vb = lb > 0 ? lb : -lb;
        bool aval, bval;
        if (va == v) {
            char newv = assign[v] ? 0 : 1;
            aval = la > 0 ? (newv != 0) : (newv == 0);
        } else {
            aval = litVal(la);
        }
        if (vb == v) {
            char newv = assign[v] ? 0 : 1;
            bval = lb > 0 ? (newv != 0) : (newv == 0);
        } else {
            bval = litVal(lb);
        }
        return aval || bval;
    };

    auto addUnsat = [&](int c) {
        if (posInUnsat[c] == -1) {
            posInUnsat[c] = (int)unsat.size();
            unsat.push_back(c);
        }
    };
    auto removeUnsat = [&](int c) {
        int p = posInUnsat[c];
        if (p != -1) {
            int last = unsat.back();
            unsat[p] = last;
            posInUnsat[last] = p;
            unsat.pop_back();
            posInUnsat[c] = -1;
        }
    };

    auto initAssignmentGreedy = [&]() {
        for (int v = 1; v <= n; ++v) {
            if (posCnt[v] > negCnt[v]) assign[v] = 1;
            else if (posCnt[v] < negCnt[v]) assign[v] = 0;
            else assign[v] = randInt(0, 1);
        }
    };
    auto initAssignmentRandom = [&]() {
        for (int v = 1; v <= n; ++v) {
            assign[v] = randInt(0, 1);
        }
    };

    auto evaluateAll = [&]() {
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        int s = 0;
        for (int i = 0; i < m; ++i) {
            bool ok = clauseVal(i);
            sat[i] = ok;
            if (!ok) addUnsat(i);
            else s++;
        }
        return s;
    };

    auto computeMakeBreak = [&](int v, int& mk, int& br) {
        mk = 0; br = 0;
        for (int c : adj[v]) {
            bool oldSat = sat[c];
            bool newSat = clauseValAfterFlip(c, v);
            if (oldSat && !newSat) br++;
            else if (!oldSat && newSat) mk++;
        }
    };

    int bestS = -1;
    double noiseP = 0.3;

    // Time budget (milliseconds)
    const int TIME_BUDGET_MS = 1500;
    auto Tstart = chrono::high_resolution_clock::now();

    int restartCount = 0;
    while (true) {
        auto now = chrono::high_resolution_clock::now();
        int elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - Tstart).count();
        if (elapsed > TIME_BUDGET_MS) break;

        if (restartCount == 0) initAssignmentGreedy();
        else initAssignmentRandom();

        int satisfied = evaluateAll();
        if (satisfied > bestS) {
            bestS = satisfied;
            bestAssign = assign;
            if (bestS == m) break;
        }

        const int MAX_STEPS = 200000; // per restart
        int steps = 0;
        int lastImproveStep = 0;

        while (!unsat.empty() && steps < MAX_STEPS) {
            steps++;
            auto now2 = chrono::high_resolution_clock::now();
            int elapsed2 = (int)chrono::duration_cast<chrono::milliseconds>(now2 - Tstart).count();
            if (elapsed2 > TIME_BUDGET_MS) break;

            int idx = randInt(0, (int)unsat.size() - 1);
            int c = unsat[idx];
            int l1 = A[c], l2 = B[c];
            int v1 = l1 > 0 ? l1 : -l1;
            int v2 = l2 > 0 ? l2 : -l2;

            int chosenV;
            if (v1 == v2) {
                chosenV = v1;
            } else {
                if (randReal() < noiseP) {
                    chosenV = (randInt(0, 1) == 0) ? v1 : v2;
                } else {
                    int mk1, br1, mk2, br2;
                    computeMakeBreak(v1, mk1, br1);
                    computeMakeBreak(v2, mk2, br2);
                    // Choose variable with smaller break, break ties by larger make, then random
                    if (br1 < br2) chosenV = v1;
                    else if (br2 < br1) chosenV = v2;
                    else {
                        int d1 = mk1 - br1;
                        int d2 = mk2 - br2;
                        if (d1 > d2) chosenV = v1;
                        else if (d2 > d1) chosenV = v2;
                        else chosenV = (randInt(0, 1) == 0) ? v1 : v2;
                    }
                }
            }

            // Flip chosenV
            assign[chosenV] ^= 1;
            // Update affected clauses
            for (int cc : adj[chosenV]) {
                bool oldSat = sat[cc];
                bool newSat = clauseVal(cc);
                if (oldSat != newSat) {
                    sat[cc] = newSat;
                    if (newSat) removeUnsat(cc);
                    else addUnsat(cc);
                }
            }

            int currentSatisfied = m - (int)unsat.size();
            if (currentSatisfied > bestS) {
                bestS = currentSatisfied;
                bestAssign = assign;
                lastImproveStep = steps;
                if (bestS == m) break;
            }

            // Optional stagnation restart within this restart
            if (steps - lastImproveStep > 50000) {
                break;
            }
        }

        restartCount++;
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}