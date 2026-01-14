#include <bits/stdc++.h>
using namespace std;

struct Node {
    int clause;
    uint8_t pos, neg; // counts of positive and negative occurrences of the variable in this clause
};
struct VarOcc {
    int var;
    uint8_t pos, neg;
};
struct Clause {
    int occSize;
    VarOcc occ[3];
    int satCount;
};

static uint64_t rng_state;
inline uint64_t rng64() {
    rng_state ^= rng_state >> 12;
    rng_state ^= rng_state << 25;
    rng_state ^= rng_state >> 27;
    return rng_state * 2685821657736338717ULL;
}
inline uint32_t rng32() { return (uint32_t)(rng64() & 0xFFFFFFFFu); }
inline int randIndex(int n) { return (int)(rng64() % (uint64_t)n); }

inline int breakscore_of_var(int v, const vector<int>& assign, const vector<Clause>& clauses, const vector<vector<Node>>& adj) {
    int br = 0;
    int av = assign[v];
    const auto& A = adj[v];
    for (const auto& n : A) {
        int sc = clauses[n.clause].satCount;
        if (sc == 0) continue;
        int t = n.pos + n.neg;
        int r = av ? n.pos : n.neg;
        int newsc = sc + t - 2*r;
        if (newsc == 0) br++;
    }
    return br;
}

inline void remove_unsat(int cid, vector<int>& where, vector<int>& unsat) {
    int idx = where[cid];
    if (idx == -1) return;
    int lastIdx = (int)unsat.size() - 1;
    int lastClause = unsat[lastIdx];
    unsat[idx] = lastClause;
    where[lastClause] = idx;
    unsat.pop_back();
    where[cid] = -1;
}

inline void add_unsat(int cid, vector<int>& where, vector<int>& unsat) {
    if (where[cid] != -1) return;
    where[cid] = (int)unsat.size();
    unsat.push_back(cid);
}

inline void flip_var(int v, vector<int>& assign, vector<Clause>& clauses, const vector<vector<Node>>& adj, vector<int>& where, vector<int>& unsat, int& satisfied) {
    int oldVal = assign[v];
    assign[v] = 1 - oldVal;
    for (const auto& n : adj[v]) {
        Clause& c = clauses[n.clause];
        int sc_old = c.satCount;
        int t = n.pos + n.neg;
        int r = oldVal ? n.pos : n.neg;
        int sc_new = sc_old + t - 2*r;
        if (sc_old == 0 && sc_new > 0) {
            satisfied++;
            remove_unsat(n.clause, where, unsat);
        } else if (sc_old > 0 && sc_new == 0) {
            satisfied--;
            add_unsat(n.clause, where, unsat);
        }
        c.satCount = sc_new;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<Clause> clauses;
    clauses.reserve(m);
    vector<vector<Node>> adj(n);
    vector<int> posTotal(n, 0), negTotal(n, 0);

    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};

        int uniqVar[3];
        uint8_t posCnt[3], negCnt[3];
        int sz = 0;

        for (int j = 0; j < 3; ++j) {
            int lit = lits[j];
            int v = abs(lit) - 1;
            bool pos = (lit > 0);
            int found = -1;
            for (int k = 0; k < sz; ++k) {
                if (uniqVar[k] == v) { found = k; break; }
            }
            if (found == -1) {
                uniqVar[sz] = v;
                posCnt[sz] = pos ? 1 : 0;
                negCnt[sz] = pos ? 0 : 1;
                ++sz;
            } else {
                if (pos) posCnt[found]++; else negCnt[found]++;
            }
        }

        Clause cl;
        cl.occSize = sz;
        cl.satCount = 0;
        for (int k = 0; k < sz; ++k) {
            cl.occ[k] = {uniqVar[k], posCnt[k], negCnt[k]};
            adj[uniqVar[k]].push_back({i, posCnt[k], negCnt[k]});
            posTotal[uniqVar[k]] += posCnt[k];
            negTotal[uniqVar[k]] += negCnt[k];
        }
        clauses.push_back(cl);
    }

    // RNG seed
    uint64_t seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(n + 0x9e3779b97f4a7c15ULL);
    seed ^= (uint64_t)(m * 0xbf58476d1ce4e5b9ULL);
    rng_state = seed ^ 0x94d049bb133111ebULL;

    // Time limit (ms)
    const int64_t TIME_LIMIT_MS = 950;
    auto time_start = chrono::steady_clock::now();
    auto time_deadline = time_start + chrono::milliseconds(TIME_LIMIT_MS);

    vector<int> bestAssign(n, 0);
    int bestS = -1;

    auto initialize_assignment = [&](vector<int>& assign, bool use_weighted) -> pair<int, vector<int>> {
        assign.assign(n, 0);
        if (use_weighted) {
            for (int i = 0; i < n; ++i) {
                if (posTotal[i] > negTotal[i]) assign[i] = 1;
                else if (posTotal[i] < negTotal[i]) assign[i] = 0;
                else assign[i] = (rng32() & 1);
            }
        } else {
            for (int i = 0; i < n; ++i) assign[i] = (rng32() & 1);
        }
        vector<int> where(m, -1);
        vector<int> unsat;
        unsat.reserve(m);

        int satisfied = 0;
        for (int i = 0; i < m; ++i) {
            int sc = 0;
            for (int k = 0; k < clauses[i].occSize; ++k) {
                int v = clauses[i].occ[k].var;
                uint8_t p = clauses[i].occ[k].pos;
                uint8_t ng = clauses[i].occ[k].neg;
                sc += assign[v] ? p : ng;
            }
            clauses[i].satCount = sc;
            if (sc == 0) {
                where[i] = (int)unsat.size();
                unsat.push_back(i);
            } else satisfied++;
        }
        return {satisfied, unsat};
    };

    const double noise = 0.36;
    const uint32_t NOISE_THRESHOLD = (uint32_t)(noise * 4294967295.0);

    int attempt = 0;
    while (true) {
        auto now = chrono::steady_clock::now();
        if (now >= time_deadline) break;

        vector<int> assign(n, 0);
        auto init = initialize_assignment(assign, attempt == 0);
        int satisfied = init.first;
        vector<int> unsat = move(init.second);
        vector<int> where(m, -1);
        for (int i = 0; i < (int)unsat.size(); ++i) where[unsat[i]] = i;

        if (satisfied > bestS) {
            bestS = satisfied;
            bestAssign = assign;
            if (bestS == m) break;
        }

        int steps = 0;
        const int CHECK_INTERVAL = 1024;
        while (true) {
            if (unsat.empty()) break;
            if ((steps & (CHECK_INTERVAL - 1)) == 0) {
                now = chrono::steady_clock::now();
                if (now >= time_deadline) break;
            }

            int cl = unsat[randIndex((int)unsat.size())];

            // Build variables in clause
            int occSize = clauses[cl].occSize;
            int vars_in_clause[3];
            for (int i = 0; i < occSize; ++i) vars_in_clause[i] = clauses[cl].occ[i].var;

            // Compute breakscore for each variable
            int brks[3];
            int zeroIdx[3];
            int zeroCnt = 0;
            int minBrk = INT_MAX;
            for (int i = 0; i < occSize; ++i) {
                int v = vars_in_clause[i];
                int br = breakscore_of_var(v, assign, clauses, adj);
                brks[i] = br;
                if (br == 0) zeroIdx[zeroCnt++] = i;
                if (br < minBrk) minBrk = br;
            }

            int chooseIdx;
            if (zeroCnt > 0) {
                chooseIdx = zeroIdx[randIndex(zeroCnt)];
            } else {
                if (rng32() <= NOISE_THRESHOLD) {
                    chooseIdx = randIndex(occSize);
                } else {
                    // pick minimal breakscore, tie random among them
                    int candIdx[3];
                    int candCnt = 0;
                    for (int i = 0; i < occSize; ++i) {
                        if (brks[i] == minBrk) candIdx[candCnt++] = i;
                    }
                    chooseIdx = candIdx[randIndex(candCnt)];
                }
            }

            int v = vars_in_clause[chooseIdx];
            flip_var(v, assign, clauses, adj, where, unsat, satisfied);

            if (satisfied > bestS) {
                bestS = satisfied;
                bestAssign = assign;
                if (bestS == m) break;
            }
            steps++;
        }
        attempt++;
        if (bestS == m) break;
    }

    if (bestS < 0) {
        bestAssign.assign(n, 0);
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (bestAssign[i] ? 1 : 0);
    }
    cout << '\n';
    return 0;
}