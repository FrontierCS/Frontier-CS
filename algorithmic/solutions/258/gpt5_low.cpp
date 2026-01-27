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

        auto query = [&](const vector<int>& nodes)->pair<int,int>{
            cout << "? " << nodes.size();
            for (int x : nodes) cout << " " << x;
            cout << endl;
            cout.flush();
            int x, d;
            if(!(cin >> x >> d)) exit(0);
            if (x == -1 && d == -1) exit(0);
            return {x, d};
        };

        // First query all nodes
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto [r, D] = query(all);

        // BFS from r to get depth and parent
        vector<int> dep(n+1, -1), par(n+1, -1);
        queue<int> q;
        dep[r] = 0;
        q.push(r);
        int maxdep = 0;
        vector<vector<int>> level; // level[d] = nodes at depth d
        level.resize(n+1);
        while(!q.empty()){
            int u = q.front(); q.pop();
            maxdep = max(maxdep, dep[u]);
            level[dep[u]].push_back(u);
            for(int v: adj[u]){
                if(dep[v]==-1){
                    dep[v]=dep[u]+1;
                    par[v]=u;
                    q.push(v);
                }
            }
        }

        // Binary search deepest depth d such that there exists a path node at depth d (query of that level returns sum == D)
        int low = 0, high = maxdep;
        while (low < high) {
            int mid = (low + high + 1) / 2;
            if (level[mid].empty()) {
                high = mid - 1;
                continue;
            }
            auto res = query(level[mid]);
            if (res.second == D) low = mid;
            else high = mid - 1;
        }

        // Query at depth low to get one endpoint s
        pair<int,int> resS = { -1, -1 };
        if (!level[low].empty()) resS = query(level[low]);
        int s = resS.first;

        // BFS from s to get distances and collect nodes at distance D
        vector<int> distS(n+1, -1);
        queue<int> q2;
        distS[s] = 0;
        q2.push(s);
        while (!q2.empty()) {
            int u = q2.front(); q2.pop();
            for (int v : adj[u]) {
                if (distS[v] == -1) {
                    distS[v] = distS[u] + 1;
                    q2.push(v);
                }
            }
        }
        vector<int> cand;
        for (int i = 1; i <= n; ++i) if (distS[i] == D) cand.push_back(i);
        auto resF = query(cand);
        int f = resF.first;

        cout << "! " << s << " " << f << endl;
        cout.flush();
        string verdict;
        if(!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }
    return 0;
}