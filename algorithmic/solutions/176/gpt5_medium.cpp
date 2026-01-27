#include <bits/stdc++.h>
using namespace std;

struct AdjEntry {
    int clause;
    unsigned char posCnt;
    unsigned char negCnt;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<array<int,3>> clauses(m);
    for (int i = 0; i < m; ++i) {
        int a,b,c;
        cin >> a >> b >> c;
        clauses[i] = {a,b,c};
    }

    // If no clauses, output any assignment (all zeros)
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Build adjacency: for each variable, unique clauses with counts of occurrences (pos/neg)
    vector<vector<AdjEntry>> adj(n+1);
    for (int i = 0; i < m; ++i) {
        int lits[3] = {clauses[i][0], clauses[i][1], clauses[i][2]};
        // Aggregate per variable within the clause
        struct VC { int var; int pos; int neg; };
        VC tmp[3];
        int sz = 0;
        for (int j = 0; j < 3; ++j) {
            int v = abs(lits[j]);
            int sgn = (lits[j] > 0) ? 1 : -1;
            int k = -1;
            for (int t = 0; t < sz; ++t) {
                if (tmp[t].var == v) { k = t; break; }
            }
            if (k == -1) {
                tmp[sz] = {v, 0, 0};
                k = sz;
                ++sz;
            }
            if (sgn > 0) tmp[k].pos++;
            else tmp[k].neg++;
        }
        for (int t = 0; t < sz; ++t) {
            adj[tmp[t].var].push_back({i, (unsigned char)tmp[t].pos, (unsigned char)tmp[t].neg});
        }
    }

    // Random generator
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937_64 rng(seed);

    vector<unsigned char> val(n+1, 0), bestVal(n+1, 0);
    vector<unsigned char> satCount(m, 0);
    vector<int> unsat; unsat.reserve(m);
    vector<int> posInUnsat(m, -1);

    auto removeUnsat = [&](int idx){
        int p = posInUnsat[idx];
        if (p == -1) return;
        int last = unsat.back();
        unsat[p] = last;
        posInUnsat[last] = p;
        unsat.pop_back();
        posInUnsat[idx] = -1;
    };
    auto addUnsat = [&](int idx){
        if (posInUnsat[idx] != -1) return;
        posInUnsat[idx] = (int)unsat.size();
        unsat.push_back(idx);
    };

    // Helper to compute literal truth
    auto litTrue = [&](int lit)->bool{
        int v = abs(lit);
        if (lit > 0) return val[v] != 0;
        else return val[v] == 0;
    };

    // Initialize assignment with a biased random towards majority polarity
    auto init_assignment = [&](){
        for (int i = 1; i <= n; ++i) {
            size_t pc = 0, nc = 0;
            for (auto &e : adj[i]) { pc += e.posCnt; nc += e.negCnt; }
            if (pc > nc) val[i] = 1;
            else if (pc < nc) val[i] = 0;
            else val[i] = (unsigned char)(rng() & 1ULL);
            // add small noise
            if ((rng() % 5) == 0) val[i] ^= 1;
        }
        fill(satCount.begin(), satCount.end(), 0);
        unsat.clear();
        fill(posInUnsat.begin(), posInUnsat.end(), -1);
        for (int i = 0; i < m; ++i) {
            int cnt = 0;
            if (litTrue(clauses[i][0])) ++cnt;
            if (litTrue(clauses[i][1])) ++cnt;
            if (litTrue(clauses[i][2])) ++cnt;
            satCount[i] = (unsigned char)cnt;
            if (cnt == 0) addUnsat(i);
        }
    };

    auto satisfied_count = [&](){ return m - (int)unsat.size(); };

    // Delta computation for flipping variable v
    auto calcDelta = [&](int v)->int{
        int delta = 0;
        unsigned char cur = val[v];
        if (cur) {
            for (const auto &e : adj[v]) {
                int i = e.clause;
                int t = satCount[i];
                int newSat = t - (int)e.posCnt + (int)e.negCnt;
                if (t == 0 && newSat > 0) ++delta;
                else if (t > 0 && newSat == 0) --delta;
            }
        } else {
            for (const auto &e : adj[v]) {
                int i = e.clause;
                int t = satCount[i];
                int newSat = t + (int)e.posCnt - (int)e.negCnt;
                if (t == 0 && newSat > 0) ++delta;
                else if (t > 0 && newSat == 0) --delta;
            }
        }
        return delta;
    };

    // Flip variable v and update structures
    auto flipVar = [&](int v){
        unsigned char old = val[v];
        val[v] ^= 1;
        if (old) {
            for (const auto &e : adj[v]) {
                int i = e.clause;
                int before = satCount[i];
                int after = before - (int)e.posCnt + (int)e.negCnt;
                satCount[i] = (unsigned char)after;
                if (before == 0 && after > 0) removeUnsat(i);
                else if (before > 0 && after == 0) addUnsat(i);
            }
        } else {
            for (const auto &e : adj[v]) {
                int i = e.clause;
                int before = satCount[i];
                int after = before + (int)e.posCnt - (int)e.negCnt;
                satCount[i] = (unsigned char)after;
                if (before == 0 && after > 0) removeUnsat(i);
                else if (before > 0 && after == 0) addUnsat(i);
            }
        }
    };

    init_assignment();
    int bestS = satisfied_count();
    for (int i = 1; i <= n; ++i) bestVal[i] = val[i];

    const int pNum = 3, pDen = 10; // noise probability 0.3
    const auto start = chrono::steady_clock::now();
    const auto timeLimit = start + chrono::milliseconds(900);
    int stepsSinceImprovement = 0;
    const int plateauLimit = 20000;

    // WalkSAT loop with restarts
    while (chrono::steady_clock::now() < timeLimit) {
        if (unsat.empty()) {
            bestS = m;
            for (int i = 1; i <= n; ++i) bestVal[i] = val[i];
            break;
        }

        int cls = unsat[rng() % unsat.size()];
        // Extract unique variables from the clause
        int lits[3] = {clauses[cls][0], clauses[cls][1], clauses[cls][2]};
        int uv[3] = {0,0,0};
        int ucnt = 0;
        for (int j = 0; j < 3; ++j) {
            int v = abs(lits[j]);
            bool found = false;
            for (int k = 0; k < ucnt; ++k) if (uv[k] == v) { found = true; break; }
            if (!found) uv[ucnt++] = v;
        }

        int varToFlip;
        if ((int)(rng() % pDen) < pNum) {
            varToFlip = uv[rng() % ucnt];
        } else {
            int bestDelta = INT_MIN;
            int candidates[3]; int csz = 0;
            for (int k = 0; k < ucnt; ++k) {
                int v = uv[k];
                int d = calcDelta(v);
                if (d > bestDelta) {
                    bestDelta = d;
                    candidates[0] = v; csz = 1;
                } else if (d == bestDelta) {
                    candidates[csz++] = v;
                }
            }
            varToFlip = candidates[rng() % csz];
        }

        flipVar(varToFlip);
        int curS = satisfied_count();
        if (curS > bestS) {
            bestS = curS;
            for (int i = 1; i <= n; ++i) bestVal[i] = val[i];
            stepsSinceImprovement = 0;
            if (bestS == m) break;
        } else {
            ++stepsSinceImprovement;
            if (stepsSinceImprovement > plateauLimit) {
                init_assignment();
                stepsSinceImprovement = 0;
            }
        }

        // Time check at intervals
        if ((rng() & 1023ULL) == 0ULL) {
            if (chrono::steady_clock::now() >= timeLimit) break;
        }
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << (int)bestVal[i];
    }
    cout << '\n';
    return 0;
}