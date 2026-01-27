#include <bits/stdc++.h>
using namespace std;

pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int v : nodes) cout << " " << v;
    cout << endl;
    cout.flush();
    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

void answer(int a, int b) {
    cout << "! " << a << " " << b << endl;
    cout.flush();
    string verdict;
    if (!(cin >> verdict)) exit(0);
    if (verdict != "Correct") exit(0);
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
        
        // First query: all nodes
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto [r, L] = ask(all);
        
        // BFS from r
        vector<int> dist(n+1, -1), par(n+1, -1);
        queue<int> q;
        q.push(r);
        dist[r] = 0;
        par[r] = -1;
        int maxDepth = 0;
        vector<vector<int>> levels(n+1);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            levels[dist[u]].push_back(u);
            maxDepth = max(maxDepth, dist[u]);
            for (int v : g[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    par[v] = u;
                    q.push(v);
                }
            }
        }
        
        // Binary search deepest level with D == L
        int left = 0, right = maxDepth;
        while (left < right) {
            int mid = (left + right + 1) / 2;
            auto [x, dsum] = ask(levels[mid]);
            if (dsum == L) left = mid;
            else right = mid - 1;
        }
        int K = left;
        
        // Get endpoint p at level K
        auto [p, dsum_p] = ask(levels[K]);
        
        // Find nxt: the child of r on path to p (if K > 0)
        int nxt = -1;
        if (K > 0) {
            int cur = p;
            while (par[cur] != r) cur = par[cur];
            nxt = cur;
        }
        
        // Build tin/tout using DFS on rooted tree at r (using par as parent)
        vector<int> tin(n+1, 0), tout(n+1, 0);
        int timer = 0;
        // Build children list based on par
        vector<vector<int>> children(n+1);
        for (int v = 1; v <= n; ++v) {
            if (par[v] != -1) children[par[v]].push_back(v);
        }
        function<void(int)> dfs = [&](int u) {
            tin[u] = ++timer;
            for (int v : children[u]) dfs(v);
            tout[u] = timer;
        };
        dfs(r);
        
        // d2 is distance from r to the other endpoint q
        int d2 = L - K;
        vector<int> cand;
        for (int v : levels[d2]) {
            if (K > 0) {
                bool inSub = (tin[nxt] <= tin[v] && tin[v] <= tout[nxt]);
                if (!inSub) cand.push_back(v);
            } else {
                cand.push_back(v);
            }
        }
        if (cand.empty()) {
            // Fallback: should not happen, but ensure non-empty
            cand = levels[d2];
        }
        
        auto [qnode, dsum_q] = ask(cand);
        
        answer(p, qnode);
    }
    return 0;
}