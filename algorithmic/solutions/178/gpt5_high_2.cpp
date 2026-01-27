#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int lit[3];
};

static inline bool litTrue(int lit, const vector<char>& X) {
    int v = abs(lit);
    char b = X[v];
    return lit > 0 ? (b != 0) : (b == 0);
}
static inline bool clauseSat(const Clause& cl, const vector<char>& X) {
    return litTrue(cl.lit[0], X) || litTrue(cl.lit[1], X) || litTrue(cl.lit[2], X);
}
static inline bool litTrueFlip(int lit, const vector<char>& X, int flipV) {
    int v = abs(lit);
    char b = X[v];
    if (v == flipV) b ^= 1;
    return lit > 0 ? (b != 0) : (b == 0);
}
static inline bool clauseSatWithFlip(const Clause& cl, const vector<char>& X, int flipV) {
    return litTrueFlip(cl.lit[0], X, flipV) || litTrueFlip(cl.lit[1], X, flipV) || litTrueFlip(cl.lit[2], X, flipV);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<int>> varOcc(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i].lit[0] = a;
        clauses[i].lit[1] = b;
        clauses[i].lit[2] = c;
        int v1 = abs(a), v2 = abs(b), v3 = abs(c);
        varOcc[v1].push_back(i);
        if (v2 != v1) varOcc[v2].push_back(i);
        if (v3 != v1 && v3 != v2) varOcc[v3].push_back(i);

        if (a > 0) posCnt[v1]++; else negCnt[v1]++;
        if (b > 0) posCnt[v2]++; else negCnt[v2]++;
        if (c > 0) posCnt[v3]++; else negCnt[v3]++;
    }

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto now = []() { return chrono::steady_clock::now(); };
    auto start = now();
    // Time budget in milliseconds; adjust if needed.
    const int TIME_BUDGET_MS = 950;
    auto deadline = start + chrono::milliseconds(TIME_BUDGET_MS);

    vector<char> bestAssign(n + 1, 0);
    int bestSat = -1;

    // Prepare a base initial assignment (majority heuristic)
    vector<char> baseAssign(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        baseAssign[v] = (posCnt[v] >= negCnt[v]) ? 1 : 0;
    }

    uniform_real_distribution<double> real01(0.0, 1.0);

    int restarts = 0;
    while (now() < deadline) {
        vector<char> X = baseAssign;
        // Add randomness to initial assignment
        double initNoise = 0.30;
        for (int v = 1; v <= n; ++v) {
            if (real01(rng) < initNoise) X[v] ^= 1;
        }

        vector<char> sat(m, 0);
        vector<int> posInUnsat(m, -1);
        vector<int> unsatList; unsatList.reserve(m);
        int s = 0;
        for (int i = 0; i < m; ++i) {
            bool ok = clauseSat(clauses[i], X);
            sat[i] = ok ? 1 : 0;
            if (ok) s++;
            else {
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            }
        }
        if (s > bestSat) {
            bestSat = s;
            bestAssign = X;
            if (bestSat == m) break;
        }

        size_t steps = 0;
        double noise = 0.33;
        auto removeUnsat = [&](int idx) {
            int p = posInUnsat[idx];
            if (p == -1) return;
            int last = unsatList.back();
            unsatList[p] = last;
            posInUnsat[last] = p;
            unsatList.pop_back();
            posInUnsat[idx] = -1;
        };
        auto addUnsat = [&](int idx) {
            if (posInUnsat[idx] != -1) return;
            posInUnsat[idx] = (int)unsatList.size();
            unsatList.push_back(idx);
        };

        // Main WalkSAT-like loop
        while (!unsatList.empty()) {
            if ((steps & 127) == 0 && now() >= deadline) break;

            int ci = unsatList[(uint64_t)rng() % unsatList.size()];
            const Clause& cl = clauses[ci];
            int v[3] = { abs(cl.lit[0]), abs(cl.lit[1]), abs(cl.lit[2]) };
            // Deduplicate variables
            int cand[3];
            int k = 0;
            cand[k++] = v[0];
            if (v[1] != cand[0]) cand[k++] = v[1];
            if (v[2] != cand[0] && (k < 2 || v[2] != cand[1])) cand[k++] = v[2];

            int chosenVar = cand[(uint64_t)rng() % k];
            if (real01(rng) >= noise) {
                // Choose variable with best delta
                int bestDelta = INT_MIN;
                int bestIdx = -1;
                int countBest = 0;
                for (int i = 0; i < k; ++i) {
                    int vv = cand[i];
                    int delta = 0;
                    const auto& occ = varOcc[vv];
                    for (int idx : occ) {
                        bool before = sat[idx];
                        bool after = clauseSatWithFlip(clauses[idx], X, vv);
                        if (before != after) delta += after ? 1 : -1;
                    }
                    if (delta > bestDelta) {
                        bestDelta = delta;
                        bestIdx = i;
                        countBest = 1;
                    } else if (delta == bestDelta) {
                        // Random tie-breaking
                        if ((uint64_t)rng() & 1) {
                            bestIdx = i;
                        }
                        countBest++;
                    }
                }
                chosenVar = cand[bestIdx];
            }

            // Flip chosen variable and update affected clauses
            X[chosenVar] ^= 1;
            const auto& occ = varOcc[chosenVar];
            for (int idx : occ) {
                bool newSat = clauseSat(clauses[idx], X);
                if (newSat != (bool)sat[idx]) {
                    if (newSat) {
                        s++;
                        sat[idx] = 1;
                        removeUnsat(idx);
                    } else {
                        s--;
                        sat[idx] = 0;
                        addUnsat(idx);
                    }
                }
            }

            if (s > bestSat) {
                bestSat = s;
                bestAssign = X;
                if (bestSat == m) break;
            }

            steps++;
        }

        restarts++;
        if (bestSat == m || now() >= deadline) break;
        // Slightly adjust base assignment with some randomness across restarts
        for (int v = 1; v <= n; ++v) {
            if ((uint64_t)rng() % 7 == 0) baseAssign[v] ^= 1;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}