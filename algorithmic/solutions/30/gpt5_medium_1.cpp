#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if(!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n+1);
        for (int i = 0; i < n-1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> parent(n+1, 0), tin(n+1, 0), tout(n+1, 0), order;
        vector<vector<int>> children(n+1);
        int timer = 0;
        function<void(int,int)> dfs = [&](int u, int p){
            parent[u] = (p == 0 ? u : p);
            tin[u] = ++timer;
            for (int v : adj[u]) if (v != p) {
                children[u].push_back(v);
                dfs(v, u);
            }
            tout[u] = timer;
            order.push_back(u); // postorder
        };
        dfs(1, 0);
        
        vector<char> alive(n+1, 1), newAlive(n+1, 0);
        int aliveCnt = n;
        
        auto inSub = [&](int u, int x) {
            return tin[u] >= tin[x] && tin[u] <= tout[x];
        };
        
        vector<int> subCnt(n+1, 0);
        
        auto recomputeSubCnt = [&]() {
            for (int v : order) {
                int cnt = alive[v] ? 1 : 0;
                for (int ch : children[v]) cnt += subCnt[ch];
                subCnt[v] = cnt;
            }
        };
        
        while (aliveCnt > 1) {
            recomputeSubCnt();
            int bestX = 1;
            int bestMax = aliveCnt; // max(subCnt[x], aliveCnt - subCnt[x])
            for (int v = 1; v <= n; ++v) {
                int a = subCnt[v];
                int b = aliveCnt - a;
                int cur = max(a, b);
                if (cur < bestMax) {
                    bestMax = cur;
                    bestX = v;
                }
            }
            cout << "? " << bestX << "\n" << flush;
            int ans;
            if(!(cin >> ans)) return 0;
            if (ans == 1) {
                // Keep only alive nodes in subtree of bestX
                aliveCnt = 0;
                for (int v = 1; v <= n; ++v) {
                    if (alive[v] && !inSub(v, bestX)) alive[v] = 0;
                    if (alive[v]) ++aliveCnt;
                }
            } else {
                // Map alive nodes not in subtree(bestX) to their parents
                fill(newAlive.begin(), newAlive.end(), 0);
                for (int v = 1; v <= n; ++v) {
                    if (alive[v] && !inSub(v, bestX)) {
                        newAlive[parent[v]] = 1;
                    }
                }
                aliveCnt = 0;
                for (int v = 1; v <= n; ++v) {
                    alive[v] = newAlive[v];
                    if (alive[v]) ++aliveCnt;
                }
                if (aliveCnt == 0) {
                    // Should not happen, but safeguard: put root as possible
                    alive[1] = 1;
                    aliveCnt = 1;
                }
            }
        }
        int answer = 1;
        for (int v = 1; v <= n; ++v) if (alive[v]) { answer = v; break; }
        cout << "! " << answer << "\n" << flush;
    }
    return 0;
}