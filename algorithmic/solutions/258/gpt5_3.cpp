#include <bits/stdc++.h>
using namespace std;

pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int x : nodes) cout << " " << x;
    cout << endl;
    cout.flush();
    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n+1);
        for (int i = 0; i < n-1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        
        vector<int> all;
        all.reserve(n);
        for (int i = 1; i <= n; ++i) all.push_back(i);
        auto p0 = ask(all);
        int r = p0.first;
        int D = p0.second;
        
        // BFS from r
        vector<int> depth(n+1, -1), parent(n+1, -1);
        queue<int> q;
        q.push(r);
        depth[r] = 0;
        int maxDepth = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (depth[v] == -1) {
                    depth[v] = depth[u] + 1;
                    parent[v] = u;
                    maxDepth = max(maxDepth, depth[v]);
                    q.push(v);
                }
            }
        }
        
        vector<vector<int>> layers(maxDepth+1);
        for (int i = 1; i <= n; ++i) {
            layers[depth[i]].push_back(i);
        }
        
        // Binary search for maximum depth dep where there exists a node on the path s-f in that layer
        int low = 0, high = maxDepth;
        int dep = 0;
        vector<int> storedX(maxDepth+1, -1);
        while (low <= high) {
            int mid = (low + high) / 2;
            auto resp = ask(layers[mid]);
            if (resp.second == D) {
                dep = mid;
                storedX[mid] = resp.first;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
        
        int u = storedX[dep];
        if (u == -1) {
            auto resp = ask(layers[dep]);
            u = resp.first;
        }
        
        // BFS from u to find nodes at distance D
        vector<int> distU(n+1, -1);
        queue<int> qu;
        qu.push(u);
        distU[u] = 0;
        while (!qu.empty()) {
            int x = qu.front(); qu.pop();
            for (int y : g[x]) {
                if (distU[y] == -1) {
                    distU[y] = distU[x] + 1;
                    qu.push(y);
                }
            }
        }
        
        vector<int> cand;
        for (int i = 1; i <= n; ++i) {
            if (distU[i] == D) cand.push_back(i);
        }
        auto resp2 = ask(cand);
        int v = resp2.first;
        
        cout << "! " << u << " " << v << endl;
        cout.flush();
        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }
    
    return 0;
}