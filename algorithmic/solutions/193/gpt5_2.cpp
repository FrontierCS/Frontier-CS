#include <bits/stdc++.h>
using namespace std;

struct Clause {
    int l[2];
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<Clause> clauses(m);
    vector<vector<int>> adj(n + 1);
    vector<int> lastSeen(n + 1, -1);
    vector<int> posCnt(n + 1, 0), negCnt(n + 1, 0);
    
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        clauses[i].l[0] = a;
        clauses[i].l[1] = b;
        int va = abs(a), vb = abs(b);
        if (a > 0) posCnt[va]++; else negCnt[va]++;
        if (b > 0) posCnt[vb]++; else negCnt[vb]++;
        if (lastSeen[va] != i) { adj[va].push_back(i); lastSeen[va] = i; }
        if (lastSeen[vb] != i) { adj[vb].push_back(i); lastSeen[vb] = i; }
    }
    
    vector<unsigned char> x(n + 1, 0);
    for (int v = 1; v <= n; ++v) {
        if (posCnt[v] >= negCnt[v]) x[v] = 1;
        else x[v] = 0;
    }
    
    auto litVal = [&](int lit)->int {
        if (lit > 0) return x[lit];
        return 1 - x[-lit];
    };
    
    // Initial satisfied clause count
    long long sat = 0;
    for (int i = 0; i < m; ++i) {
        int v0 = litVal(clauses[i].l[0]);
        int v1 = litVal(clauses[i].l[1]);
        if (v0 || v1) ++sat;
    }
    
    // Compute initial gains
    vector<int> gain(n + 1, 0);
    for (int i = 0; i < m; ++i) {
        int a = clauses[i].l[0], b = clauses[i].l[1];
        int v0 = litVal(a), v1 = litVal(b);
        int va = abs(a), vb = abs(b);
        if (v1 == 0) {
            if (v0 == 1) gain[va] -= 1;
            else gain[va] += 1;
        }
        if (v0 == 0) {
            if (v1 == 1) gain[vb] -= 1;
            else gain[vb] += 1;
        }
    }
    
    // Local improvement: flip variables with positive gain until none
    while (true) {
        int bestVar = 0;
        int bestGain = 0;
        for (int v = 1; v <= n; ++v) {
            if (gain[v] > bestGain) {
                bestGain = gain[v];
                bestVar = v;
            }
        }
        if (bestGain <= 0 || bestVar == 0) break;
        
        int v = bestVar;
        // Apply flip
        sat += gain[v];
        x[v] ^= 1;
        
        // Update gains for variables affected by this flip via clause-level recomputation
        for (int cid : adj[v]) {
            Clause &c = clauses[cid];
            int a = c.l[0], b = c.l[1];
            int va = abs(a), vb = abs(b);
            
            int v0_new = litVal(a);
            int v1_new = litVal(b);
            int v0_old = v0_new, v1_old = v1_new;
            if (abs(a) == v) v0_old = 1 - v0_new;
            if (abs(b) == v) v1_old = 1 - v1_new;
            
            // Contributions to gain for variable at side 0
            int contr_old_0 = 0, contr_new_0 = 0;
            if (v1_old == 0) contr_old_0 = (v0_old ? -1 : +1);
            if (v1_new == 0) contr_new_0 = (v0_new ? -1 : +1);
            gain[va] += contr_new_0 - contr_old_0;
            
            // Contributions to gain for variable at side 1
            int contr_old_1 = 0, contr_new_1 = 0;
            if (v0_old == 0) contr_old_1 = (v1_old ? -1 : +1);
            if (v0_new == 0) contr_new_1 = (v1_new ? -1 : +1);
            gain[vb] += contr_new_1 - contr_old_1;
        }
    }
    
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << int(x[i]);
    }
    cout << '\n';
    return 0;
}