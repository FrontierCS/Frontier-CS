#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b, c;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<Clause> clauses(m);
    for (int i = 0; i < m; ++i) {
        cin >> clauses[i].a >> clauses[i].b >> clauses[i].c;
    }
    if (n == 0) {
        cout << "\n";
        return 0;
    }
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << "\n";
        return 0;
    }

    // Build occurrence lists
    vector<vector<pair<int,bool>>> occ(n+1); // (clause index, isPositive)
    for (int i = 0; i < m; ++i) {
        int lits[3] = {clauses[i].a, clauses[i].b, clauses[i].c};
        for (int k = 0; k < 3; ++k) {
            int lit = lits[k];
            int var = abs(lit);
            bool pos = lit > 0;
            if (var >= 1 && var <= n) occ[var].push_back({i, pos});
        }
    }

    auto start = chrono::steady_clock::now();
    const long long timeLimitMs = 1800;

    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    vector<int> bestAssign(n+1, 0);
    int bestS = -1;

    auto timeExceeded = [&]() {
        auto now = chrono::steady_clock::now();
        return chrono::duration_cast<chrono::milliseconds>(now - start).count() > timeLimitMs;
    };

    uniform_real_distribution<double> prob(0.0, 1.0);

    while (!timeExceeded()) {
        // Random initial assignment
        vector<int> val(n+1, 0);
        for (int i = 1; i <= n; ++i) val[i] = rng() & 1;

        vector<int> satCount(m, 0);
        vector<int> unsatList;
        unsatList.reserve(m);
        vector<int> posInUnsat(m, -1);

        auto litTrue = [&](int var, bool pos, const vector<int>& assign)->bool{
            return pos ? (assign[var] == 1) : (assign[var] == 0);
        };

        int s = 0;
        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            if (litTrue(abs(clauses[i].a), clauses[i].a > 0, val)) ++cnt;
            if (litTrue(abs(clauses[i].b), clauses[i].b > 0, val)) ++cnt;
            if (litTrue(abs(clauses[i].c), clauses[i].c > 0, val)) ++cnt;
            satCount[i] = cnt;
            if (cnt > 0) ++s;
            else {
                posInUnsat[i] = (int)unsatList.size();
                unsatList.push_back(i);
            }
        }

        auto addUnsat = [&](int ci){
            if (posInUnsat[ci] == -1) {
                posInUnsat[ci] = (int)unsatList.size();
                unsatList.push_back(ci);
            }
        };
        auto removeUnsat = [&](int ci){
            int p = posInUnsat[ci];
            if (p == -1) return;
            int last = unsatList.back();
            unsatList[p] = last;
            posInUnsat[last] = p;
            unsatList.pop_back();
            posInUnsat[ci] = -1;
        };

        auto evalDelta = [&](int v)->int{
            int delta = 0;
            for (auto &pr : occ[v]) {
                int ci = pr.first;
                bool pos = pr.second;
                bool lt = litTrue(v, pos, val);
                int sc = satCount[ci];
                if (sc == 0 && !lt) delta += 1; // becomes satisfied
                else if (sc == 1 && lt) delta -= 1; // becomes unsatisfied
            }
            return delta;
        };

        auto flipVar = [&](int v){
            // Update all affected clauses, then flip val[v]
            for (auto &pr : occ[v]) {
                int ci = pr.first;
                bool pos = pr.second;
                bool lt = litTrue(v, pos, val); // before flip
                int pre = satCount[ci];
                satCount[ci] += lt ? -1 : +1;
                int post = satCount[ci];
                if (pre == 0 && post > 0) { ++s; removeUnsat(ci); }
                else if (pre > 0 && post == 0) { --s; addUnsat(ci); }
            }
            val[v] ^= 1;
        };

        int itersSinceImprovement = 0;
        const double walkProb = 0.2;
        const double randomWhenStuckProb = 0.7; // when no improving flip
        int localBestS = s;

        for (int steps = 0; steps < 100000000; ++steps) {
            if (timeExceeded()) break;
            if (s > bestS) {
                bestS = s;
                bestAssign = val;
                localBestS = s;
                itersSinceImprovement = 0;
                if (s == m) break;
            } else {
                ++itersSinceImprovement;
            }

            int chosenVar = -1;

            bool doWalk = (!unsatList.empty() && prob(rng) < walkProb);

            if (!doWalk) {
                // Greedy: choose var with maximum delta
                int bestDelta = INT_MIN;
                vector<int> candidates;
                candidates.reserve(n);
                for (int v = 1; v <= n; ++v) {
                    int d = evalDelta(v);
                    if (d > bestDelta) {
                        bestDelta = d;
                        candidates.clear();
                        candidates.push_back(v);
                    } else if (d == bestDelta) {
                        candidates.push_back(v);
                    }
                }
                if (bestDelta > 0) {
                    chosenVar = candidates[rng() % candidates.size()];
                } else {
                    // Stuck: random walk preferred
                    if (!unsatList.empty() && prob(rng) < randomWhenStuckProb) {
                        doWalk = true;
                    } else {
                        // pick from candidates even if <=0 to move
                        chosenVar = candidates[rng() % candidates.size()];
                    }
                }
            }

            if (doWalk) {
                int ci = unsatList[rng() % unsatList.size()];
                int lits[3] = {clauses[ci].a, clauses[ci].b, clauses[ci].c};
                chosenVar = abs(lits[rng() % 3]);
            }

            if (chosenVar == -1) {
                // Should not happen, fallback random variable
                chosenVar = (rng() % n) + 1;
            }

            flipVar(chosenVar);

            if (itersSinceImprovement > 10000 && prob(rng) < 0.05) break; // restart
        }

        if (bestS == m) break;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << "\n";
    return 0;
}