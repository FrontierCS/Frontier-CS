#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int var[3];
    bool pos[3];
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct Solver {
    int n, m;
    vector<Clause> clauses;
    vector<vector<int>> occ; // unique clause indices per variable

    mt19937_64 rng;

    vector<uint8_t> val, bestVal;
    int satisfied = 0, bestSat = -1;

    vector<uint8_t> trueCount;  // 0..3
    vector<int> unsat;
    vector<int> posInUnsat;

    Solver(int n_, int m_, vector<Clause> clauses_, vector<vector<int>> occ_)
        : n(n_), m(m_), clauses(std::move(clauses_)), occ(std::move(occ_)) {
        uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
        seed = splitmix64(seed);
        rng.seed(seed);
        val.assign(n, 0);
        bestVal.assign(n, 0);
        trueCount.assign(m, 0);
        posInUnsat.assign(m, -1);
    }

    inline bool litTrue(int c, int i) const {
        int v = clauses[c].var[i];
        bool x = val[v] != 0;
        return clauses[c].pos[i] ? x : !x;
    }

    inline void addUnsat(int c) {
        if (posInUnsat[c] != -1) return;
        posInUnsat[c] = (int)unsat.size();
        unsat.push_back(c);
    }

    inline void removeUnsat(int c) {
        int p = posInUnsat[c];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posInUnsat[last] = p;
        unsat.pop_back();
        posInUnsat[c] = -1;
    }

    int initStateRandom() {
        for (int i = 0; i < n; i++) val[i] = (uint8_t)(rng() & 1ULL);

        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);

        satisfied = 0;
        for (int c = 0; c < m; c++) {
            int t = 0;
            t += (int)litTrue(c, 0);
            t += (int)litTrue(c, 1);
            t += (int)litTrue(c, 2);
            trueCount[c] = (uint8_t)t;
            if (t == 0) addUnsat(c);
            else satisfied++;
        }
        return satisfied;
    }

    inline int computeGain(int v) {
        int gain = 0;
        for (int c : occ[v]) {
            int t = (int)trueCount[c];
            int occCount = 0, oldTrueOcc = 0;
            for (int i = 0; i < 3; i++) {
                if (clauses[c].var[i] == v) {
                    occCount++;
                    oldTrueOcc += (int)litTrue(c, i);
                }
            }
            int newTrueOcc = occCount - oldTrueOcc;
            int t2 = t - oldTrueOcc + newTrueOcc;
            if (t == 0 && t2 > 0) gain++;
            else if (t > 0 && t2 == 0) gain--;
        }
        return gain;
    }

    inline void flipVar(int v) {
        // Update clauses using OLD assignment (before toggle), then toggle.
        for (int c : occ[v]) {
            int t = (int)trueCount[c];
            int occCount = 0, oldTrueOcc = 0;
            for (int i = 0; i < 3; i++) {
                if (clauses[c].var[i] == v) {
                    occCount++;
                    oldTrueOcc += (int)litTrue(c, i);
                }
            }
            int newTrueOcc = occCount - oldTrueOcc;
            int t2 = t - oldTrueOcc + newTrueOcc;

            if (t == 0 && t2 > 0) {
                removeUnsat(c);
                satisfied++;
            } else if (t > 0 && t2 == 0) {
                addUnsat(c);
                satisfied--;
            }
            trueCount[c] = (uint8_t)t2;
        }
        val[v] ^= 1;
    }

    inline int pickUnsatClause() {
        return unsat[(size_t)(rng() % (uint64_t)unsat.size())];
    }

    void solve(double timeLimitSeconds = 1.8) {
        if (m == 0) {
            bestSat = 0;
            fill(bestVal.begin(), bestVal.end(), 0);
            return;
        }

        auto tStart = chrono::steady_clock::now();
        auto tEnd = tStart + chrono::duration<double>(timeLimitSeconds);

        const double randomPickProb = 0.5;
        const int maxStepsPerRestart = 60000;

        while (chrono::steady_clock::now() < tEnd) {
            initStateRandom();
            if (satisfied > bestSat) {
                bestSat = satisfied;
                bestVal = val;
                if (bestSat == m) return;
            }

            int steps = 0;
            int localBest = satisfied;
            int stepsNoImprove = 0;

            while (steps < maxStepsPerRestart && !unsat.empty()) {
                if ((steps & 255) == 0) {
                    if (chrono::steady_clock::now() >= tEnd) break;
                }

                int c = pickUnsatClause();

                int cand[3];
                int k = 0;
                for (int i = 0; i < 3; i++) {
                    int v = clauses[c].var[i];
                    bool seen = false;
                    for (int j = 0; j < k; j++) if (cand[j] == v) { seen = true; break; }
                    if (!seen) cand[k++] = v;
                }

                int vflip;
                double r = (double)((rng() >> 11) * (1.0 / 9007199254740992.0)); // [0,1)
                if (r < randomPickProb) {
                    vflip = cand[rng() % (uint64_t)k];
                } else {
                    int bestGain = INT_MIN;
                    int bestIdx = -1;
                    int ties[3], nt = 0;
                    for (int i = 0; i < k; i++) {
                        int v = cand[i];
                        int g = computeGain(v);
                        if (g > bestGain) {
                            bestGain = g;
                            nt = 0;
                            ties[nt++] = v;
                        } else if (g == bestGain) {
                            ties[nt++] = v;
                        }
                    }
                    vflip = ties[rng() % (uint64_t)nt];
                }

                flipVar(vflip);
                steps++;

                if (satisfied > bestSat) {
                    bestSat = satisfied;
                    bestVal = val;
                    if (bestSat == m) return;
                }

                if (satisfied > localBest) {
                    localBest = satisfied;
                    stepsNoImprove = 0;
                } else {
                    stepsNoImprove++;
                    if (stepsNoImprove > 8000) break; // restart
                }
            }
        }
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses(m);
    vector<vector<int>> occ(n);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        int arr[3] = {a, b, c};
        bool used[50] = {};
        for (int j = 0; j < 3; j++) {
            int x = arr[j];
            int v = abs(x) - 1;
            clauses[i].var[j] = v;
            clauses[i].pos[j] = (x > 0);
        }
        for (int j = 0; j < 3; j++) {
            int v = clauses[i].var[j];
            if (!used[v]) {
                used[v] = true;
                occ[v].push_back(i);
            }
        }
    }

    Solver solver(n, m, std::move(clauses), std::move(occ));
    solver.solve(1.8);

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (int)solver.bestVal[i];
    }
    cout << '\n';
    return 0;
}