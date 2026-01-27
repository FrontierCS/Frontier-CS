#include <bits/stdc++.h>
using namespace std;

struct ClauseVar {
    int var;
    int posCount;
    int negCount;
};

struct VarClause {
    int cid;
    int posCount;
    int negCount;
};

struct HeapNode {
    int gain;
    int ver;
    int var;
    bool operator<(const HeapNode& other) const {
        if (gain != other.gain) return gain < other.gain; // max-heap
        return ver < other.ver;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<array<int,3>> raw(m);
    for (int i = 0; i < m; ++i) {
        int a,b,c;
        cin >> a >> b >> c;
        raw[i] = {a,b,c};
    }
    // Edge case: no clauses
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            if (i > 1) cout << ' ';
            cout << 0;
        }
        cout << '\n';
        return 0;
    }

    // Build per-clause unique variable entries with counts
    vector<vector<ClauseVar>> clauseVars(m);
    vector<unordered_map<int, pair<int,int>>> temp(m);
    temp.reserve(m);
    for (int i = 0; i < m; ++i) {
        auto [a,b,c] = raw[i];
        int lits[3] = {a,b,c};
        for (int k = 0; k < 3; ++k) {
            int lit = lits[k];
            int v = abs(lit);
            int s = (lit > 0) ? 1 : -1;
            auto &mp = temp[i];
            auto &pr = mp[v];
            if (s == 1) pr.first += 1;
            else pr.second += 1;
        }
    }
    for (int i = 0; i < m; ++i) {
        clauseVars[i].reserve(3);
        for (auto &kv : temp[i]) {
            clauseVars[i].push_back({kv.first, kv.second.first, kv.second.second});
        }
        temp[i].clear(); temp[i].rehash(0);
    }
    temp.clear();

    // Build per-variable list of clauses
    vector<vector<VarClause>> varOcc(n+1);
    for (int i = 0; i < m; ++i) {
        for (auto &cv : clauseVars[i]) {
            varOcc[cv.var].push_back({i, cv.posCount, cv.negCount});
        }
    }

    // Random engine
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    // Assignment
    vector<int> val(n+1);
    for (int i = 1; i <= n; ++i) val[i] = (rng() & 1);

    // Clause true counts
    vector<int> clauseTrueCount(m, 0);
    auto litTruth = [&](int v, int sign) -> int {
        // sign +1 for positive, -1 for neg
        return (sign == 1) ? val[v] : (1 - val[v]);
    };
    for (int i = 0; i < m; ++i) {
        int tc = 0;
        for (auto &cv : clauseVars[i]) {
            if (cv.posCount) tc += cv.posCount * val[cv.var];
            if (cv.negCount) tc += cv.negCount * (1 - val[cv.var]);
        }
        clauseTrueCount[i] = tc;
    }

    // Unsatisfied clause list
    vector<int> unsatPos(m, -1);
    vector<int> unsatList;
    unsatList.reserve(m);
    int satisfied = 0;
    for (int i = 0; i < m; ++i) {
        if (clauseTrueCount[i] > 0) satisfied++;
        else {
            unsatPos[i] = (int)unsatList.size();
            unsatList.push_back(i);
        }
    }

    // Gains
    vector<int> gain(n+1, 0);
    auto deltaForFlipInClause = [&](int vval, int pc, int nc)->int{
        // change in number of true literals in the clause when flipping a variable with vval, pc, nc.
        // before: pc*vval + nc*(1 - vval)
        // after:  pc*(1 - vval) + nc*(vval)
        int before = pc * vval + nc * (1 - vval);
        int after  = pc * (1 - vval) + nc * vval;
        return after - before;
    };
    for (int v = 1; v <= n; ++v) {
        int g = 0;
        for (auto &vc : varOcc[v]) {
            int cid = vc.cid;
            int beforeTC = clauseTrueCount[cid];
            bool wasSat = beforeTC > 0;
            int d = deltaForFlipInClause(val[v], vc.posCount, vc.negCount);
            bool willSat = (beforeTC + d) > 0;
            g += (int)willSat - (int)wasSat;
        }
        gain[v] = g;
    }

    // Build quick access map from clause to its variable entries for iterative updates
    // Also, for each clause, list of (var, pc, nc)
    // Already clauseVars.

    // Heap with lazy updates
    vector<int> ver(n+1, 0);
    priority_queue<HeapNode> pq;
    for (int v = 1; v <= n; ++v) pq.push({gain[v], ver[v], v});

    auto push_update = [&](int v){
        ver[v]++;
        pq.push({gain[v], ver[v], v});
    };

    auto addUnsat = [&](int cid){
        if (unsatPos[cid] != -1) return;
        unsatPos[cid] = (int)unsatList.size();
        unsatList.push_back(cid);
    };
    auto removeUnsat = [&](int cid){
        int pos = unsatPos[cid];
        if (pos == -1) return;
        int last = unsatList.back();
        unsatList[pos] = last;
        unsatPos[last] = pos;
        unsatList.pop_back();
        unsatPos[cid] = -1;
    };

    auto flip_variable = [&](int v){
        int prevVal = val[v];
        val[v] ^= 1;

        // For each affected clause, update clauseTrueCount, satisfied, unsatList, and gains of vars in clause
        for (auto &vc : varOcc[v]) {
            int cid = vc.cid;
            int beforeTC = clauseTrueCount[cid];
            bool beforeSat = beforeTC > 0;

            int deltaV = deltaForFlipInClause(prevVal, vc.posCount, vc.negCount);
            int afterTC = beforeTC + deltaV;
            clauseTrueCount[cid] = afterTC;
            bool afterSat = afterTC > 0;
            if (beforeSat != afterSat) {
                if (afterSat) {
                    satisfied++;
                    removeUnsat(cid);
                } else {
                    satisfied--;
                    addUnsat(cid);
                }
            }

            // Update gains for variables in this clause
            for (auto &cv : clauseVars[cid]) {
                int u = cv.var;
                int pc = cv.posCount, nc = cv.negCount;
                // old contribution for u
                int du = deltaForFlipInClause(val[u], pc, nc); // note val[u] is current (after any flips prior in this call). For v, val[v] after flip which is correct for contribution computation.
                bool oldWasSat = beforeTC > 0;
                bool oldWillSat = (beforeTC + du) > 0;
                int oldContr = (int)oldWillSat - (int)oldWasSat;

                bool newWasSat = afterTC > 0;
                bool newWillSat = (afterTC + du) > 0;
                int newContr = (int)newWillSat - (int)newWasSat;

                int deltaGain = newContr - oldContr;
                if (deltaGain != 0) {
                    gain[u] += deltaGain;
                    push_update(u);
                }
            }
        }
    };

    auto get_best_variable = [&]()->int{
        while (!pq.empty()) {
            auto top = pq.top();
            if (top.ver == ver[top.var] && top.gain == gain[top.var]) {
                return top.var;
            } else {
                pq.pop();
            }
        }
        // rebuild heap if empty (shouldn't happen)
        for (int v = 1; v <= n; ++v) pq.push({gain[v], ver[v], v});
        return pq.top().var;
    };

    auto pick_from_unsat_clause = [&]()->int{
        if (unsatList.empty()) {
            // fallback random
            uniform_int_distribution<int> dist(1, n);
            return dist(rng);
        }
        uniform_int_distribution<int> distC(0, (int)unsatList.size()-1);
        int cid = unsatList[distC(rng)];
        // choose variable in this clause with highest overall gain
        int bestVar = clauseVars[cid][0].var;
        int bestG = INT_MIN;
        for (auto &cv : clauseVars[cid]) {
            int u = cv.var;
            if (gain[u] > bestG) {
                bestG = gain[u];
                bestVar = u;
            }
        }
        return bestVar;
    };

    auto start_time = chrono::steady_clock::now();
    const double TIME_LIMIT_SEC = 0.95; // conservative
    auto time_ok = [&](){
        auto now = chrono::steady_clock::now();
        double sec = chrono::duration<double>(now - start_time).count();
        return sec < TIME_LIMIT_SEC;
    };

    // Local search
    while (time_ok() && satisfied < m) {
        int bestVar = get_best_variable();
        int bestGain = gain[bestVar];
        int chosen;
        if (bestGain > 0) {
            chosen = bestVar;
        } else {
            chosen = pick_from_unsat_clause();
        }
        flip_variable(chosen);
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << val[i];
    }
    cout << '\n';
    return 0;
}