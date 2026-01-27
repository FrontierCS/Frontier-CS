#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int var[3];
    int sign[3]; // +1 for positive, -1 for negation
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    
    vector<Clause> clauses(m);
    vector<int> posCnt(n+1, 0), negCnt(n+1, 0);
    for (int i = 0; i < m; ++i) {
        int a, b, c;
        cin >> a >> b >> c;
        int lits[3] = {a, b, c};
        for (int j = 0; j < 3; ++j) {
            int x = lits[j];
            clauses[i].var[j] = abs(x);
            clauses[i].sign[j] = (x > 0) ? 1 : -1;
            if (x > 0) posCnt[abs(x)]++;
            else negCnt[abs(x)]++;
        }
    }
    
    // Initial assignment: majority
    vector<int> x(n+1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] >= negCnt[v]) x[v] = 1;
        else x[v] = 0;
    }
    
    // Occurrences
    vector<vector<pair<int,int>>> occ(n+1);
    occ.assign(n+1, {});
    for (int i = 0; i < m; ++i) {
        for (int j = 0; j < 3; ++j) {
            int v = clauses[i].var[j];
            occ[v].push_back({i, j});
        }
    }
    
    // t[i] = number of true literals in clause i
    vector<int> t(m, 0);
    auto litVal = [&](int v, int sgn)->int{
        return (sgn == 1) ? x[v] : (1 - x[v]);
    };
    for (int i = 0; i < m; ++i) {
        int cnt = 0;
        for (int j = 0; j < 3; ++j) {
            int v = clauses[i].var[j];
            int s = clauses[i].sign[j];
            cnt += litVal(v, s);
        }
        t[i] = cnt;
    }
    
    // delta[v] = change in satisfied clauses if flip v
    vector<int> delta(n+1, 0);
    auto compute_delta_var = [&](int v)->int{
        int d = 0;
        for (auto [cid, lid] : occ[v]) {
            int ti = t[cid];
            int sgn = clauses[cid].sign[lid];
            int val = (sgn == 1) ? x[v] : (1 - x[v]);
            if (ti == 0) {
                if (val == 0) d += 1;
            } else if (ti == 1) {
                if (val == 1) d -= 1;
            }
        }
        return d;
    };
    
    for (int v = 1; v <= n; ++v) {
        delta[v] = compute_delta_var(v);
    }
    
    // Max-heap for best improvement
    priority_queue<pair<int,int>> pq;
    for (int v = 1; v <= n; ++v) pq.push({delta[v], v});
    
    vector<char> mark(n+1, 0);
    vector<int> affectedVars; affectedVars.reserve(64);
    
    int maxFlips = 200000; // safety cap
    while (!pq.empty() && maxFlips-- > 0) {
        auto [d, v] = pq.top(); pq.pop();
        if (d != delta[v]) continue; // stale
        if (d <= 0) break; // no improvement possible
        
        int x_old = x[v];
        x[v] = 1 - x_old;
        
        // Update t for affected clauses and collect affected variables
        affectedVars.clear();
        for (auto [cid, lid] : occ[v]) {
            int sgn = clauses[cid].sign[lid];
            int val_old = (sgn == 1) ? x_old : (1 - x_old);
            if (val_old == 1) t[cid] -= 1;
            else t[cid] += 1;
            // mark variables in this clause
            for (int j = 0; j < 3; ++j) {
                int u = clauses[cid].var[j];
                if (!mark[u]) {
                    mark[u] = 1;
                    affectedVars.push_back(u);
                }
            }
        }
        // Recompute delta for affected variables
        for (int u : affectedVars) {
            delta[u] = compute_delta_var(u);
            pq.push({delta[u], u});
            mark[u] = 0;
        }
    }
    
    // Output assignment
    for (int v = 1; v <= n; ++v) {
        if (v > 1) cout << ' ';
        cout << x[v];
    }
    cout << '\n';
    return 0;
}