#include <bits/stdc++.h>
using namespace std;

inline bool evalClauseNoFlip(const array<int,3>& cl, const vector<int>& assign) {
    for (int k = 0; k < 3; ++k) {
        int lit = cl[k];
        int var = abs(lit);
        int val = assign[var];
        if (lit > 0) {
            if (val) return true;
        } else {
            if (!val) return true;
        }
    }
    return false;
}

inline bool evalClauseWithFlip(const array<int,3>& cl, const vector<int>& assign, int flipVar) {
    for (int k = 0; k < 3; ++k) {
        int lit = cl[k];
        int var = abs(lit);
        int val = assign[var];
        if (var == flipVar) val ^= 1;
        if (lit > 0) {
            if (val) return true;
        } else {
            if (!val) return true;
        }
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int,3>> clause(m);
    vector<vector<int>> varOcc(n + 1);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        clause[i] = {a, b, c};
        int vs[3] = {abs(a), abs(b), abs(c)};
        sort(vs, vs + 3);
        int k = int(unique(vs, vs + 3) - vs);
        for (int j = 0; j < k; ++j) {
            varOcc[vs[j]].push_back(i);
        }
    }

    vector<int> bestAssign(n + 1, 0);

    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    vector<int> curAssign(n + 1);
    vector<char> clauseSat(m);

    long long maxOps = 80000000LL;
    long long approxIter = maxOps / (9LL * m);
    long long TOTAL_ITERS_LL = approxIter;
    if (TOTAL_ITERS_LL < 2000) TOTAL_ITERS_LL = 2000;
    if (TOTAL_ITERS_LL > 30000) TOTAL_ITERS_LL = 30000;
    int TOTAL_ITERS = (int)TOTAL_ITERS_LL;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> bit01(0, 1);

    int bestSat = -1;
    int remaining = TOTAL_ITERS;

    while (remaining > 0) {
        int localIter = min(1000, remaining);
        remaining -= localIter;

        for (int i = 1; i <= n; ++i) {
            curAssign[i] = bit01(rng);
        }

        int curSat = 0;
        for (int i = 0; i < m; ++i) {
            bool sat = evalClauseNoFlip(clause[i], curAssign);
            clauseSat[i] = sat;
            if (sat) ++curSat;
        }

        if (curSat > bestSat) {
            bestSat = curSat;
            bestAssign = curAssign;
            if (bestSat == m) break;
        }

        for (int step = 0; step < localIter && curSat < m; ++step) {
            int bestV = -1;
            int bestDelta = INT_MIN;

            for (int v = 1; v <= n; ++v) {
                const auto &occList = varOcc[v];
                int occSize = (int)occList.size();
                if (occSize == 0) continue;

                int delta = 0;
                for (int idx = 0; idx < occSize; ++idx) {
                    int cid = occList[idx];
                    bool before = clauseSat[cid];
                    bool after = evalClauseWithFlip(clause[cid], curAssign, v);
                    if (before && !after) --delta;
                    else if (!before && after) ++delta;
                }
                if (delta > bestDelta) {
                    bestDelta = delta;
                    bestV = v;
                }
            }

            if (bestDelta <= 0 || bestV == -1) break;

            curAssign[bestV] ^= 1;
            const auto &occList = varOcc[bestV];
            int occSize = (int)occList.size();
            for (int idx = 0; idx < occSize; ++idx) {
                int cid = occList[idx];
                bool newVal = evalClauseNoFlip(clause[cid], curAssign);
                if (!clauseSat[cid] && newVal) ++curSat;
                else if (clauseSat[cid] && !newVal) --curSat;
                clauseSat[cid] = newVal;
            }

            if (curSat > bestSat) {
                bestSat = curSat;
                bestAssign = curAssign;
                if (bestSat == m) break;
            }
        }

        if (bestSat == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        cout << bestAssign[i] << (i == n ? '\n' : ' ');
    }

    return 0;
}