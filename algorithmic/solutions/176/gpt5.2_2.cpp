#include <bits/stdc++.h>
using namespace std;

struct Occ {
    int clause;
    int lit; // signed literal
};

static inline int litTruth(int lit, int varVal) {
    // varVal is 0/1
    return (lit > 0) ? varVal : (varVal ^ 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<array<int, 3>> clauses(m);
    vector<vector<Occ>> occ(n);
    occ.assign(n, {});
    occ.shrink_to_fit();
    occ.assign(n, {});

    for (int i = 0; i < m; i++) {
        int a, b, c;
        cin >> a >> b >> c;
        clauses[i] = {a, b, c};
        int lits[3] = {a, b, c};
        for (int k = 0; k < 3; k++) {
            int lit = lits[k];
            int v = abs(lit) - 1;
            if (0 <= v && v < n) occ[v].push_back({i, lit});
        }
    }

    if (m == 0) {
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> bitDist(0, 1);
    uniform_real_distribution<double> realDist(0.0, 1.0);

    vector<int> mark(m, 0), tmpTotal(m, 0), tmpTrue(m, 0);
    int tag = 1;

    vector<int> assign(n, 0), bestAssign(n, 0);
    vector<int> trueCnt(m, 0);
    vector<int> unsat;
    vector<int> posInUnsat(m, -1);
    int satisfied = 0, bestSatisfied = -1;

    auto addUnsat = [&](int c) {
        if (posInUnsat[c] != -1) return;
        posInUnsat[c] = (int)unsat.size();
        unsat.push_back(c);
    };
    auto removeUnsat = [&](int c) {
        int p = posInUnsat[c];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posInUnsat[last] = p;
        unsat.pop_back();
        posInUnsat[c] = -1;
    };

    auto resetAssignmentRandom = [&]() {
        for (int i = 0; i < n; i++) assign[i] = bitDist(rng);

        satisfied = 0;
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);

        for (int ci = 0; ci < m; ci++) {
            int cnt = 0;
            auto &cl = clauses[ci];
            for (int k = 0; k < 3; k++) {
                int lit = cl[k];
                int v = abs(lit) - 1;
                cnt += litTruth(lit, assign[v]);
            }
            trueCnt[ci] = cnt;
            if (cnt == 0) addUnsat(ci);
            else satisfied++;
        }
    };

    auto prepareVar = [&](int v, vector<int> &touched) {
        touched.clear();
        if (++tag == INT_MAX) {
            tag = 1;
            fill(mark.begin(), mark.end(), 0);
        }
        for (const auto &o : occ[v]) {
            int c = o.clause;
            if (mark[c] != tag) {
                mark[c] = tag;
                tmpTotal[c] = 0;
                tmpTrue[c] = 0;
                touched.push_back(c);
            }
            tmpTotal[c]++;
            tmpTrue[c] += litTruth(o.lit, assign[v]);
        }
    };

    auto deltaFlipPrepared = [&](const vector<int> &touched) -> int {
        int delta = 0;
        for (int c : touched) {
            int cnt = trueCnt[c];
            int newCnt = cnt + (tmpTotal[c] - 2 * tmpTrue[c]);
            if (cnt == 0 && newCnt > 0) delta++;
            else if (cnt > 0 && newCnt == 0) delta--;
        }
        return delta;
    };

    auto flipVar = [&](int v) {
        vector<int> touched;
        prepareVar(v, touched);
        assign[v] ^= 1;
        for (int c : touched) {
            int cnt = trueCnt[c];
            int newCnt = cnt + (tmpTotal[c] - 2 * tmpTrue[c]);
            if (cnt == 0 && newCnt > 0) {
                satisfied++;
                removeUnsat(c);
            } else if (cnt > 0 && newCnt == 0) {
                satisfied--;
                addUnsat(c);
            }
            trueCnt[c] = newCnt;
        }
    };

    auto start = chrono::steady_clock::now();
    auto elapsedSec = [&]() -> double {
        return chrono::duration<double>(chrono::steady_clock::now() - start).count();
    };

    const double TIME_LIMIT = 1.80;
    const double NOISE_PROB = 0.20;

    while (elapsedSec() < TIME_LIMIT) {
        resetAssignmentRandom();

        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestAssign = assign;
            if (bestSatisfied == m) break;
        }

        long long steps = 0;
        long long maxSteps = 200000; // per restart cap; time-based exit anyway

        while (!unsat.empty() && steps < maxSteps && elapsedSec() < TIME_LIMIT) {
            steps++;

            int ci = unsat[(size_t)(rng() % unsat.size())];
            auto &cl = clauses[ci];

            int vars[3] = {abs(cl[0]) - 1, abs(cl[1]) - 1, abs(cl[2]) - 1};
            int cand[3];
            int k = 0;
            for (int i = 0; i < 3; i++) {
                bool ok = true;
                for (int j = 0; j < k; j++) if (cand[j] == vars[i]) { ok = false; break; }
                if (ok) cand[k++] = vars[i];
            }

            int chosen = cand[rng() % (unsigned)k];
            if (realDist(rng) >= NOISE_PROB) {
                int bestDelta = INT_MIN;
                int bestV = chosen;
                for (int i = 0; i < k; i++) {
                    int v = cand[i];
                    vector<int> touched;
                    prepareVar(v, touched);
                    int d = deltaFlipPrepared(touched);
                    if (d > bestDelta || (d == bestDelta && (rng() & 1))) {
                        bestDelta = d;
                        bestV = v;
                    }
                }
                chosen = bestV;
            }

            flipVar(chosen);

            if (satisfied > bestSatisfied) {
                bestSatisfied = satisfied;
                bestAssign = assign;
                if (bestSatisfied == m) break;
            }

            if ((steps & 1023LL) == 0 && elapsedSec() >= TIME_LIMIT) break;
        }

        if (bestSatisfied == m) break;
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << bestAssign[i];
    }
    cout << '\n';
    return 0;
}