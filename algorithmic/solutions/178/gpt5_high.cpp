#include <bits/stdc++.h>
using namespace std;

struct Clause3 {
    int v[3];
    bool s[3]; // true if positive literal
};

struct VarClauseOcc {
    int clause;
    uint8_t pos; // number of positive occurrences in clause
    uint8_t neg; // number of negative occurrences in clause
};

static inline uint64_t splitmix64(uint64_t& x) {
    uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Solver {
    int n, m;
    vector<Clause3> clauses;
    vector<vector<VarClauseOcc>> varClauses; // per variable, list of unique clauses with counts
    vector<int> satCount; // number of satisfied literals in each clause
    vector<int> assign; // current assignment
    vector<int> bestAssign;
    int satisfied = 0, bestSatisfied = -1;
    vector<int> unsat; // indices of unsatisfied clauses
    vector<int> posInUnsat; // position in unsat vector, -1 if not present

    uint64_t rng_state;

    Solver(int n, int m): n(n), m(m) {
        clauses.resize(m);
        varClauses.assign(n, {});
        satCount.assign(m, 0);
        assign.assign(n, 0);
        bestAssign.assign(n, 0);
        posInUnsat.assign(m, -1);
        rng_state = chrono::high_resolution_clock::now().time_since_epoch().count();
    }

    inline uint32_t rndu() { return (uint32_t)splitmix64(rng_state); }
    inline int rndInt(int l, int r) { return l + (int)(rndu() % (uint32_t)(r - l + 1)); }
    inline bool rndProb(double p) {
        // Convert rndu to double in [0,1)
        return (rndu() >> 11) * (1.0/9007199254740992.0) < p;
    }

    void addUnsat(int c) {
        if (posInUnsat[c] != -1) return;
        posInUnsat[c] = (int)unsat.size();
        unsat.push_back(c);
    }
    void removeUnsat(int c) {
        int pos = posInUnsat[c];
        if (pos == -1) return;
        int last = unsat.back();
        unsat[pos] = last;
        posInUnsat[last] = pos;
        unsat.pop_back();
        posInUnsat[c] = -1;
    }

    void parse_input_and_build(const vector<array<int,3>>& input_clauses) {
        // Fill clauses and varClauses (aggregated by clause per variable)
        for (int i = 0; i < m; ++i) {
            for (int k = 0; k < 3; ++k) {
                int lit = input_clauses[i][k];
                int v = abs(lit) - 1;
                bool sgn = (lit > 0);
                clauses[i].v[k] = v;
                clauses[i].s[k] = sgn;
                // add to varClauses[v], aggregate by clause
                auto &vec = varClauses[v];
                int found = -1;
                for (int t = 0; t < (int)vec.size(); ++t) {
                    if (vec[t].clause == i) { found = t; break; }
                }
                if (found == -1) {
                    VarClauseOcc oc;
                    oc.clause = i;
                    oc.pos = 0;
                    oc.neg = 0;
                    if (sgn) oc.pos = 1; else oc.neg = 1;
                    vec.push_back(oc);
                } else {
                    if (sgn) vec[found].pos++; else vec[found].neg++;
                }
            }
        }
    }

    void initialize_majority() {
        vector<int> posCnt(n,0), negCnt(n,0);
        for (int i = 0; i < m; ++i) {
            for (int k = 0; k < 3; ++k) {
                int v = clauses[i].v[k];
                if (clauses[i].s[k]) posCnt[v]++; else negCnt[v]++;
            }
        }
        for (int v = 0; v < n; ++v) {
            if (posCnt[v] > negCnt[v]) assign[v] = 1;
            else if (posCnt[v] < negCnt[v]) assign[v] = 0;
            else assign[v] = rndu() & 1;
        }
        evaluate_current();
    }

    void initialize_random() {
        for (int v = 0; v < n; ++v) assign[v] = rndu() & 1;
        evaluate_current();
    }

    void evaluate_current() {
        fill(satCount.begin(), satCount.end(), 0);
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            for (int k = 0; k < 3; ++k) {
                int v = clauses[i].v[k];
                bool sgn = clauses[i].s[k];
                if ((assign[v] == 1 && sgn) || (assign[v] == 0 && !sgn)) cnt++;
            }
            satCount[i] = cnt;
            if (cnt == 0) addUnsat(i);
        }
        satisfied = m - (int)unsat.size();
        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestAssign = assign;
        }
    }

    void flipVar(int v) {
        int oldval = assign[v];
        assign[v] ^= 1;
        // Update all clauses where v appears
        for (const auto& oc : varClauses[v]) {
            int c = oc.clause;
            int oldsc = satCount[c];
            int delta = 0;
            if (oldval == 1) {
                // pos satisfied become unsat; neg unsat become sat
                delta = (int)oc.neg - (int)oc.pos;
            } else {
                // old 0 -> new 1: pos become sat; neg become unsat
                delta = (int)oc.pos - (int)oc.neg;
            }
            if (delta != 0) {
                satCount[c] += delta;
                int newsc = satCount[c];
                if (oldsc == 0 && newsc > 0) { removeUnsat(c); satisfied++; }
                else if (oldsc > 0 && newsc == 0) { addUnsat(c); satisfied--; }
            }
        }
        if (satisfied > bestSatisfied) {
            bestSatisfied = satisfied;
            bestAssign = assign;
        }
    }

    struct DeltaInfo {
        int gain; // make - break
        int brk;
    };

    DeltaInfo computeDelta(int v) {
        int make = 0, brk = 0;
        int oldval = assign[v];
        for (const auto& oc : varClauses[v]) {
            int c = oc.clause;
            int oldsc = satCount[c];
            int delta;
            if (oldval == 1) delta = (int)oc.neg - (int)oc.pos;
            else delta = (int)oc.pos - (int)oc.neg;
            int newsc = oldsc + delta;
            if (oldsc == 0 && newsc > 0) make++;
            else if (oldsc > 0 && newsc == 0) brk++;
        }
        return {make - brk, brk};
    }

    void search(double timeLimitSec) {
        auto start = chrono::high_resolution_clock::now();
        double noise = 0.5;

        int restart = 0;
        while (true) {
            auto now = chrono::high_resolution_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > timeLimitSec) break;

            if (restart == 0) initialize_majority();
            else initialize_random();

            int stepsWithoutImprove = 0;
            const int MAX_STEPS_LOCAL = 1000000000; // practically limited by time
            for (int step = 0; step < MAX_STEPS_LOCAL; ++step) {
                if (satisfied == m) return; // found perfect
                // time check occasionally
                if ((step & 1023) == 0) {
                    now = chrono::high_resolution_clock::now();
                    elapsed = chrono::duration<double>(now - start).count();
                    if (elapsed > timeLimitSec) break;
                }

                if (unsat.empty()) break;

                int c = unsat[rndInt(0, (int)unsat.size() - 1)];
                int vars[3] = {clauses[c].v[0], clauses[c].v[1], clauses[c].v[2]};

                // Compute delta/brk for variables in this clause
                int zeroBreakVars[3]; int zbCnt = 0;
                int bestVar = vars[0];
                int bestGain = INT_MIN;
                int bestBrk = INT_MAX;

                for (int idx = 0; idx < 3; ++idx) {
                    int v = vars[idx];
                    DeltaInfo di = computeDelta(v);
                    if (di.brk == 0) {
                        zeroBreakVars[zbCnt++] = v;
                    }
                    // Select by minimal break, then by maximal gain
                    if (di.brk < bestBrk || (di.brk == bestBrk && di.gain > bestGain) || (di.brk == bestBrk && di.gain == bestGain && (rndu() & 1))) {
                        bestBrk = di.brk;
                        bestGain = di.gain;
                        bestVar = v;
                    }
                }

                int chosenVar;
                if (zbCnt > 0) {
                    chosenVar = zeroBreakVars[rndInt(0, zbCnt - 1)];
                } else if (rndProb(noise)) {
                    chosenVar = vars[rndInt(0, 2)];
                } else {
                    chosenVar = bestVar;
                }

                int before = satisfied;
                flipVar(chosenVar);
                if (satisfied > before) stepsWithoutImprove = 0;
                else stepsWithoutImprove++;

                // occasional random kick if stuck
                if (stepsWithoutImprove > 20000) {
                    // Randomly flip a variable from a random unsatisfied clause
                    if (!unsat.empty()) {
                        int cc = unsat[rndInt(0, (int)unsat.size() - 1)];
                        int vv = clauses[cc].v[rndInt(0,2)];
                        flipVar(vv);
                    }
                    stepsWithoutImprove = 0;
                }
            }
            restart++;
        }
    }

    void solve() {
        if (m == 0) {
            bestAssign.assign(n, 0);
            return;
        }
        // Time limit selection: modest to be safe
        double timeLimitSec = 0.95;
        search(timeLimitSec);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<array<int,3>> input_clauses(m);
    for (int i = 0; i < m; ++i) {
        int a,b,c;
        cin >> a >> b >> c;
        input_clauses[i] = {a,b,c};
    }
    Solver solver(n, m);
    solver.parse_input_and_build(input_clauses);
    solver.solve();

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << solver.bestAssign[i];
    }
    cout << '\n';
    return 0;
}