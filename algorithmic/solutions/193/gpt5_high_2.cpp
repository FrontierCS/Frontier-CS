#include <bits/stdc++.h>
using namespace std;

static inline bool litValue(int lit, const vector<unsigned char>& x) {
    int v = lit > 0 ? lit : -lit;
    bool val = x[v];
    return lit > 0 ? val : !val;
}
static inline bool litValueWithToggled(int lit, int var, const vector<unsigned char>& x) {
    int v = lit > 0 ? lit : -lit;
    bool val = x[v];
    if (v == var) val = !val;
    return lit > 0 ? val : !val;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<int> A(m), B(m);
    vector<int> freqPos(n + 1, 0), freqNeg(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        A[i] = a; B[i] = b;
        int va = abs(a), vb = abs(b);
        if (a > 0) freqPos[va]++; else freqNeg[va]++;
        if (b > 0) freqPos[vb]++; else freqNeg[vb]++;
    }
    vector<vector<int>> occ(n + 1);
    occ.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int va = abs(A[i]), vb = abs(B[i]);
        if (va == vb) {
            occ[va].push_back(i);
        } else {
            occ[va].push_back(i);
            occ[vb].push_back(i);
        }
    }

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count() ^ (uint64_t)(uintptr_t(new int)));
    auto randBool = [&](double p)->bool {
        uniform_real_distribution<double> dist(0.0, 1.0);
        return dist(rng) < p;
    };
    auto randIndex = [&](size_t up)->size_t {
        uniform_int_distribution<size_t> dist(0, up - 1);
        return dist(rng);
    };

    auto now = [&](){ return chrono::steady_clock::now(); };
    auto start = now();
    auto deadline = start + chrono::milliseconds(950);

    vector<unsigned char> bestX(n + 1, 0);
    long long bestS = -1;

    auto run_attempt = [&](bool randomized, double noise) {
        vector<unsigned char> x(n + 1, 0);
        if (!randomized) {
            for (int i = 1; i <= n; ++i) {
                if (freqPos[i] > freqNeg[i]) x[i] = 1;
                else if (freqPos[i] < freqNeg[i]) x[i] = 0;
                else x[i] = rng() & 1;
            }
        } else {
            for (int i = 1; i <= n; ++i) x[i] = rng() & 1;
        }

        vector<unsigned char> sat(m, 0);
        vector<int> posInUnsat(m, -1);
        vector<int> unsat;
        unsat.reserve(m);
        long long S = 0;
        for (int i = 0; i < m; ++i) {
            bool s = (litValue(A[i], x) || litValue(B[i], x));
            sat[i] = s ? 1 : 0;
            if (!s) {
                posInUnsat[i] = (int)unsat.size();
                unsat.push_back(i);
            }
            if (s) S++;
        }

        if (S > bestS) {
            bestS = S;
            bestX = x;
        }
        if (unsat.empty()) return;

        size_t maxSteps = max(10000, min(200000, 10 * m));
        for (size_t step = 0; step < maxSteps; ++step) {
            if ((step & 1023) == 0 && now() > deadline) break;
            if (unsat.empty()) break;

            int ci = unsat[randIndex(unsat.size())];
            int v1 = abs(A[ci]);
            int v2 = abs(B[ci]);
            int chosenVar;

            if (v1 == v2) {
                chosenVar = v1;
            } else if (randBool(noise)) {
                chosenVar = (rng() & 1) ? v1 : v2;
            } else {
                long long d1 = 0, d2 = 0;
                for (int c : occ[v1]) {
                    int prev = sat[c];
                    bool ns = (litValueWithToggled(A[c], v1, x) || litValueWithToggled(B[c], v1, x));
                    d1 += (int)ns - prev;
                }
                for (int c : occ[v2]) {
                    int prev = sat[c];
                    bool ns = (litValueWithToggled(A[c], v2, x) || litValueWithToggled(B[c], v2, x));
                    d2 += (int)ns - prev;
                }
                if (d1 > d2) chosenVar = v1;
                else if (d2 > d1) chosenVar = v2;
                else chosenVar = (rng() & 1) ? v1 : v2;
            }

            x[chosenVar] ^= 1;

            for (int c : occ[chosenVar]) {
                int prev = sat[c];
                bool ns = (litValue(A[c], x) || litValue(B[c], x));
                if (prev != (int)ns) {
                    sat[c] = ns ? 1 : 0;
                    if (ns) {
                        // remove from unsat
                        int pos = posInUnsat[c];
                        if (pos != -1) {
                            int last = unsat.back();
                            unsat[pos] = last;
                            posInUnsat[last] = pos;
                            unsat.pop_back();
                            posInUnsat[c] = -1;
                        }
                        S++;
                    } else {
                        // add to unsat
                        if (posInUnsat[c] == -1) {
                            posInUnsat[c] = (int)unsat.size();
                            unsat.push_back(c);
                        }
                        S--;
                    }
                }
            }

            if (S > bestS) {
                bestS = S;
                bestX = x;
                if ((int)bestS == m) break;
            }
        }
    };

    // First attempt: heuristic initialization
    run_attempt(false, 0.3);

    // Additional random restarts until time runs out
    while (now() < deadline) {
        run_attempt(true, 0.4);
        if (bestS == m) break;
    }

    // Output best assignment
    for (int i = 1; i <= n; ++i) {
        cout << (bestX[i] ? 1 : 0) << (i == n ? '\n' : ' ');
    }

    return 0;
}