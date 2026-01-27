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

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if(!(cin >> t)) return 0;
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
        // Query all nodes
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto [root, D] = ask(all);

        // BFS from root to get levels
        vector<int> dist(n+1, -1), par(n+1, -1);
        queue<int> q;
        dist[root] = 0;
        q.push(root);
        int maxDepth = 0;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            maxDepth = max(maxDepth, dist[u]);
            for (int v : g[u]) if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                par[v] = u;
                q.push(v);
            }
        }
        vector<vector<int>> levels(maxDepth+1);
        for (int v = 1; v <= n; ++v) {
            levels[dist[v]].push_back(v);
        }

        // Binary search the farthest on-path node from root
        int low = 0, high = maxDepth;
        int s = root;
        while (low <= high) {
            int mid = (low + high) / 2;
            auto res = ask(levels[mid]);
            if (res.second == D) {
                s = res.first;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }

        // Find the other endpoint: nodes at distance D from s
        vector<int> distS(n+1, -1);
        queue<int> qs;
        distS[s] = 0;
        qs.push(s);
        while (!qs.empty()) {
            int u = qs.front(); qs.pop();
            for (int v : g[u]) if (distS[v] == -1) {
                distS[v] = distS[u] + 1;
                qs.push(v);
            }
        }
        vector<int> cand;
        for (int v = 1; v <= n; ++v) if (distS[v] == D) cand.push_back(v);
        auto [f, D2] = ask(cand);

        cout << "! " << s << " " << f << endl;
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }
    return 0;
}