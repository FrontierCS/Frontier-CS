#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i] = {a, b};
    }

    if (m == 0) {
        // Any assignment is fine
        for (int i = 1; i <= n; ++i) {
            cout << 0 << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // Build occurrence lists: for each variable, which clauses it appears in
    vector<vector<int>> occ(n + 1);
    for (int i = 0; i < m; ++i) {
        int a = clauses[i].a;
        int b = clauses[i].b;
        int va = abs(a), vb = abs(b);
        if (va == vb) {
            occ[va].push_back(i);
        } else {
            occ[va].push_back(i);
            occ[vb].push_back(i);
        }
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> val(n + 1);
    vector<int> bestVal(n + 1);
    vector<int> satCount(m);
    vector<int> posInUnsat(m);
    vector<int> unsat;
    unsat.reserve(m);

    auto initRandom = [&]() -> int {
        for (int i = 1; i <= n; ++i) val[i] = (int)(rng() & 1);

        fill(satCount.begin(), satCount.end(), 0);
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);

        int curSat = 0;
        for (int i = 0; i < m; ++i) {
            int a = clauses[i].a, b = clauses[i].b;
            int va = abs(a), vb = abs(b);
            bool av = (a > 0) ? (bool)val[va] : !val[va];
            bool bv = (b > 0) ? (bool)val[vb] : !val[vb];
            int cnt = (av ? 1 : 0) + (bv ? 1 : 0);
            satCount[i] = cnt;
            if (cnt > 0) {
                ++curSat;
            } else {
                posInUnsat[i] = (int)unsat.size();
                unsat.push_back(i);
            }
        }
        return curSat;
    };

    int curSat = initRandom();
    int bestSat = curSat;
    bestVal = val;

    auto computeDelta = [&](int v) -> int {
        int delta = 0;
        const auto &vec = occ[v];
        for (int idx = 0; idx < (int)vec.size(); ++idx) {
            int ci = vec[idx];
            bool satBefore = satCount[ci] > 0;

            Clause &cl = clauses[ci];
            int a = cl.a, b = cl.b;
            int va = abs(a), vb = abs(b);

            bool aAfter, bAfter;
            if (va == v) {
                if (a > 0) aAfter = !((bool)val[v]);
                else       aAfter = (bool)val[v];
            } else {
                if (a > 0) aAfter = (bool)val[va];
                else       aAfter = !((bool)val[va]);
            }

            if (vb == v) {
                if (b > 0) bAfter = !((bool)val[v]);
                else       bAfter = (bool)val[v];
            } else {
                if (b > 0) bAfter = (bool)val[vb];
                else       bAfter = !((bool)val[vb]);
            }

            bool satAfter = aAfter || bAfter;
            if (!satBefore && satAfter) ++delta;
            else if (satBefore && !satAfter) --delta;
        }
        return delta;
    };

    auto flipVar = [&](int v) {
        val[v] ^= 1;
        const auto &vec = occ[v];
        for (int idx = 0; idx < (int)vec.size(); ++idx) {
            int ci = vec[idx];
            Clause &cl = clauses[ci];
            int a = cl.a, b = cl.b;
            int va = abs(a), vb = abs(b);

            bool av = (a > 0) ? (bool)val[va] : !val[va];
            bool bv = (b > 0) ? (bool)val[vb] : !val[vb];
            int newCnt = (av ? 1 : 0) + (bv ? 1 : 0);
            int oldCnt = satCount[ci];

            if (oldCnt == 0 && newCnt > 0) {
                int pos = posInUnsat[ci];
                if (pos != -1) {
                    int last = unsat.back();
                    unsat[pos] = last;
                    posInUnsat[last] = pos;
                    unsat.pop_back();
                    posInUnsat[ci] = -1;
                }
            } else if (oldCnt > 0 && newCnt == 0) {
                if (posInUnsat[ci] == -1) {
                    posInUnsat[ci] = (int)unsat.size();
                    unsat.push_back(ci);
                }
            }
            satCount[ci] = newCnt;
        }
    };

    using namespace std::chrono;
    auto start = steady_clock::now();
    const double TIME_LIMIT = 0.95;
    const long long CHECK_FREQ = 1024;
    const int GREEDY_PROB = 700; // out of 1000

    for (long long steps = 0;; ++steps) {
        if ((steps & (CHECK_FREQ - 1)) == 0) {
            auto now = steady_clock::now();
            double t = duration<double>(now - start).count();
            if (t > TIME_LIMIT) break;
        }

        if (unsat.empty()) {
            bestSat = m;
            bestVal = val;
            break;
        }

        int ci = unsat[(size_t)(rng() % unsat.size())];
        Clause &cl = clauses[ci];
        int var1 = abs(cl.a);
        int var2 = abs(cl.b);

        int chosenVar;
        int delta;

        if (var1 == var2) {
            chosenVar = var1;
            delta = computeDelta(chosenVar);
        } else {
            if ((int)(rng() % 1000) < GREEDY_PROB) {
                int d1 = computeDelta(var1);
                int d2 = computeDelta(var2);
                if (d1 > d2) {
                    chosenVar = var1;
                    delta = d1;
                } else if (d2 > d1) {
                    chosenVar = var2;
                    delta = d2;
                } else {
                    if (rng() & 1) {
                        chosenVar = var1;
                        delta = d1;
                    } else {
                        chosenVar = var2;
                        delta = d2;
                    }
                }
            } else {
                chosenVar = (rng() & 1) ? var1 : var2;
                delta = computeDelta(chosenVar);
            }
        }

        flipVar(chosenVar);
        curSat += delta;

        if (curSat > bestSat) {
            bestSat = curSat;
            bestVal = val;
            if (bestSat == m) break;
        }
    }

    for (int i = 1; i <= n; ++i) {
        cout << (bestVal[i] ? 1 : 0);
        if (i < n) cout << ' ';
    }
    cout << '\n';

    return 0;
}