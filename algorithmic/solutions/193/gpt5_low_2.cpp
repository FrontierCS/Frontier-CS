#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int a, b; // literals: positive x means var x, negative -x means NOT x
};

static inline bool evalLit(int lit, const vector<char>& x) {
    if (lit > 0) return x[lit];
    else return !x[-lit];
}

static inline int varOf(int lit) {
    return abs(lit);
}

// Contribution of clause c to delta of variable v under current assignment x.
// Precondition: v is one of the variables in clause c.
int clauseContribution(const Clause& c, int v, const vector<char>& x) {
    int va = varOf(c.a), vb = varOf(c.b);
    bool valA = evalLit(c.a, x);
    bool valB = evalLit(c.b, x);
    if (va == v) {
        // flipping v toggles valA
        if (valA && !valB) return -1;
        if (!valA && !valB) return +1;
        return 0;
    } else {
        // must be vb == v
        if (valB && !valA) return -1;
        if (!valB && !valA) return +1;
        return 0;
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
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i] = {a, b};
    }

    // Adjacency: for each variable, list of (clause index, which literal index 0/1)
    vector<vector<pair<int,int>>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int va = varOf(clauses[i].a);
        int vb = varOf(clauses[i].b);
        if (va >= 1 && va <= n) adj[va].push_back({i, 0});
        if (vb >= 1 && vb <= n) adj[vb].push_back({i, 1});
    }

    // Initialize assignment randomly
    vector<char> x(n + 1, 0);
    std::mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    for (int i = 1; i <= n; ++i) {
        x[i] = (rng() & 1);
    }

    // Clause satisfaction
    vector<char> sat(m, 0);
    int satisfied = 0;
    for (int i = 0; i < m; ++i) {
        bool val = evalLit(clauses[i].a, x) || evalLit(clauses[i].b, x);
        sat[i] = val;
        if (val) ++satisfied;
    }

    // Delta for each variable
    vector<int> delta(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        int d = 0;
        for (auto [ci, side] : adj[v]) {
            d += clauseContribution(clauses[ci], v, x);
        }
        delta[v] = d;
    }

    // Hill climbing: repeatedly flip variable with max positive delta
    while (true) {
        int bestV = -1;
        int bestDelta = 0;
        for (int v = 1; v <= n; ++v) {
            if (delta[v] > bestDelta) {
                bestDelta = delta[v];
                bestV = v;
            }
        }
        if (bestV == -1) break; // no improving flip

        int u = bestV;

        // Gather info for affected clauses before flip
        struct Info { int ci; int other; int before_contrib; char oldSat; };
        vector<Info> infos;
        infos.reserve(adj[u].size());
        for (auto [ci, side] : adj[u]) {
            int otherVar;
            if (side == 0) {
                otherVar = varOf(clauses[ci].b);
            } else {
                otherVar = varOf(clauses[ci].a);
            }
            int before_contrib = 0;
            if (otherVar != u) {
                before_contrib = clauseContribution(clauses[ci], otherVar, x);
            }
            infos.push_back({ci, otherVar, before_contrib, sat[ci]});
        }

        // Flip variable u
        x[u] ^= 1;

        // Update delta[u]
        delta[u] = -delta[u];

        // Update clauses and deltas of neighboring variables
        for (auto &inf : infos) {
            int ci = inf.ci;
            bool newSat = evalLit(clauses[ci].a, x) || evalLit(clauses[ci].b, x);
            if (inf.oldSat != newSat) {
                if (newSat) ++satisfied; else --satisfied;
                sat[ci] = newSat;
            }
            int v = inf.other;
            if (v != u) {
                int after_contrib = clauseContribution(clauses[ci], v, x);
                delta[v] += (after_contrib - inf.before_contrib);
            }
        }
    }

    // Output assignment
    for (int i = 1; i <= n; ++i) {
        cout << (int)x[i] << (i == n ? '\n' : ' ');
    }

    return 0;
}