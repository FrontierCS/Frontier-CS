#include <bits/stdc++.h>
using namespace std;

pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (size_t i = 0; i < nodes.size(); ++i) {
        cout << " " << nodes[i];
    }
    cout << "\n";
    cout.flush();
    int x, d;
    if (!(cin >> x >> d)) {
        exit(0);
    }
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
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto first = ask(all);
        int root = first.first;
        int D = first.second;

        // BFS from root
        vector<int> dist(n + 1, -1), par(n + 1, -1);
        queue<int> q;
        q.push(root);
        dist[root] = 0;
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) if (dist[to] == -1) {
                dist[to] = dist[v] + 1;
                par[to] = v;
                q.push(to);
            }
        }
        int maxDepth = 0;
        for (int i = 1; i <= n; ++i) if (dist[i] > maxDepth) maxDepth = dist[i];

        vector<vector<int>> layers(maxDepth + 1);
        for (int i = 1; i <= n; ++i) layers[dist[i]].push_back(i);

        int low = 0, high = maxDepth;
        while (low < high) {
            int mid = (low + high + 1) / 2;
            auto res = ask(layers[mid]);
            if (res.second == D) low = mid;
            else high = mid - 1;
        }
        int deep = low;

        auto res_deep = ask(layers[deep]);
        int v = res_deep.first;

        // BFS from v
        vector<int> distV(n + 1, -1);
        queue<int> q2;
        q2.push(v);
        distV[v] = 0;
        while (!q2.empty()) {
            int cur = q2.front(); q2.pop();
            for (int to : g[cur]) if (distV[to] == -1) {
                distV[to] = distV[cur] + 1;
                q2.push(to);
            }
        }
        vector<int> cand;
        for (int i = 1; i <= n; ++i) if (distV[i] == D) cand.push_back(i);

        auto res2 = ask(cand);
        int w = res2.first;

        cout << "! " << v << " " << w << "\n";
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") {
            return 0;
        }
    }
    return 0;
}