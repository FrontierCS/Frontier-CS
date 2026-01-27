#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int v1, v2;
    uint8_t s1, s2; // 1 for positive, 0 for negated
};

static inline void addUnsat(vector<int>& unsat, vector<int>& pos, int idx) {
    if (pos[idx] == -1) {
        pos[idx] = (int)unsat.size();
        unsat.push_back(idx);
    }
}
static inline void removeUnsat(vector<int>& unsat, vector<int>& pos, int idx) {
    int p = pos[idx];
    if (p != -1) {
        int last = unsat.back();
        unsat[p] = last;
        pos[last] = p;
        unsat.pop_back();
        pos[idx] = -1;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<Clause> clauses(m);
    vector<vector<int>> adj(n + 1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        int va = abs(a), vb = abs(b);
        uint8_t sa = (a > 0) ? 1 : 0;
        uint8_t sb = (b > 0) ? 1 : 0;
        clauses[i] = {va, vb, sa, sb};
        posCnt[va] += sa ? 1 : 0;
        negCnt[va] += sa ? 0 : 1;
        posCnt[vb] += sb ? 1 : 0;
        negCnt[vb] += sb ? 0 : 1;
        adj[va].push_back(i);
        if (vb != va) adj[vb].push_back(i);
    }

    // Initial assignment: polarity heuristic
    vector<uint8_t> assign(n + 1, 0);
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] > negCnt[v]) assign[v] = 1;
        else if (posCnt[v] < negCnt[v]) assign[v] = 0;
        else assign[v] = (uint8_t)(rng() & 1ULL);
    }

    auto initState = [&](vector<uint8_t>& asg, vector<int>& breakcnt, vector<int>& posInUnsat, vector<int>& unsat) {
        fill(breakcnt.begin(), breakcnt.end(), 0);
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        unsat.clear();
        for (int i = 0; i < m; ++i) {
            const Clause &c = clauses[i];
            int t1 = c.s1 ? asg[c.v1] : (1 - asg[c.v1]);
            int t2 = c.s2 ? asg[c.v2] : (1 - asg[c.v2]);
            int sat = t1 | t2;
            if (!sat) addUnsat(unsat, posInUnsat, i);
            if (c.v1 != c.v2) {
                if (t1 && !t2) breakcnt[c.v1]++;
                if (t2 && !t1) breakcnt[c.v2]++;
            } else {
                if (t1 && t2) breakcnt[c.v1]++;
            }
        }
    };

    auto flipVar = [&](int v, vector<uint8_t>& asg, vector<int>& breakcnt, vector<int>& posInUnsat, vector<int>& unsat) {
        for (int ci : adj[v]) {
            const Clause &c = clauses[ci];
            int v1 = c.v1, v2 = c.v2;
            int t1 = c.s1 ? asg[v1] : (1 - asg[v1]);
            int t2 = c.s2 ? asg[v2] : (1 - asg[v2]);
            int sat_before = t1 | t2;
            if (v1 != v2) {
                int b1_before = (t1 & (!t2));
                int b2_before = (t2 & (!t1));
                int t1p = (v1 == v) ? (t1 ^ 1) : t1;
                int t2p = (v2 == v) ? (t2 ^ 1) : t2;
                int sat_after = t1p | t2p;
                if (!sat_before && sat_after) removeUnsat(unsat, posInUnsat, ci);
                else if (sat_before && !sat_after) addUnsat(unsat, posInUnsat, ci);
                int b1_after = (t1p & (!t2p));
                int b2_after = (t2p & (!t1p));
                if (b1_before != b1_after) breakcnt[v1] += (b1_after - b1_before);
                if (b2_before != b2_after) breakcnt[v2] += (b2_after - b2_before);
            } else {
                // same variable appears twice (possibly with same or opposite sign)
                int t1p = t1 ^ 1; // flipping v toggles both literals
                int t2p = t2 ^ 1;
                int sat_after = t1p | t2p;
                if (!sat_before && sat_after) removeUnsat(unsat, posInUnsat, ci);
                else if (sat_before && !sat_after) addUnsat(unsat, posInUnsat, ci);
                int b_before = (t1 & t2);
                int b_after = (t1p & t2p);
                if (b_before != b_after) breakcnt[v1] += (b_after - b_before); // v1==v2
            }
        }
        asg[v] ^= 1;
    };

    vector<int> breakcnt(n + 1, 0);
    vector<int> posInUnsat(m, -1);
    vector<int> unsat;
    unsat.reserve(m);

    initState(assign, breakcnt, posInUnsat, unsat);

    vector<uint8_t> bestAssign = assign;
    int bestUnsat = (int)unsat.size();

    if (m > 0 && bestUnsat > 0) {
        const double noise = 0.3;
        auto start = chrono::steady_clock::now();
        const int timeBudgetMs = 900; // ~0.9s
        // multiple restarts
        int restart = 0;
        while (true) {
            // Time check
            auto now = chrono::steady_clock::now();
            int elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - start).count();
            if (elapsed >= timeBudgetMs) break;

            // For subsequent restarts, randomize initial assignment a bit
            if (restart > 0) {
                for (int v = 1; v <= n; ++v) {
                    // small random flip probability
                    if ((rng() & 1023ULL) < 5ULL) assign[v] ^= 1;
                }
                initState(assign, breakcnt, posInUnsat, unsat);
            }

            int stepsPerRestart = max(20000, min(400000, m * 10));
            for (int step = 0; step < stepsPerRestart; ++step) {
                if (unsat.empty()) break;
                // Time check every 1024 steps
                if ((step & 1023) == 0) {
                    now = chrono::steady_clock::now();
                    elapsed = (int)chrono::duration_cast<chrono::milliseconds>(now - start).count();
                    if (elapsed >= timeBudgetMs) break;
                }
                int ci = unsat[rng() % unsat.size()];
                const Clause &c = clauses[ci];
                int v1 = c.v1, v2 = c.v2;
                int choose_v;
                if (v1 == v2) {
                    choose_v = v1;
                } else {
                    int bc1 = breakcnt[v1];
                    int bc2 = breakcnt[v2];
                    double r = std::generate_canonical<double, 10>(rng);
                    if (r < noise) {
                        choose_v = (rng() & 1ULL) ? v1 : v2;
                    } else {
                        if (bc1 < bc2) choose_v = v1;
                        else if (bc2 < bc1) choose_v = v2;
                        else choose_v = (rng() & 1ULL) ? v1 : v2;
                    }
                }
                flipVar(choose_v, assign, breakcnt, posInUnsat, unsat);

                if ((int)unsat.size() < bestUnsat) {
                    bestUnsat = (int)unsat.size();
                    bestAssign = assign;
                    if (bestUnsat == 0) break;
                }
            }
            if (bestUnsat == 0) break;
            restart++;
        }
    }

    // Output best assignment found
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestAssign[i];
    }
    cout << '\n';
    return 0;
}