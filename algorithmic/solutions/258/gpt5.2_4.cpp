#include <bits/stdc++.h>
using namespace std;

static pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << (int)nodes.size();
    for (int v : nodes) cout << ' ' << v;
    cout << '\n' << flush;

    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto [root, D] = ask(all);

        vector<int> dist(n + 1, -1);
        queue<int> q;
        dist[root] = 0;
        q.push(root);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) {
                if (dist[to] != -1) continue;
                dist[to] = dist[v] + 1;
                q.push(to);
            }
        }

        vector<vector<int>> level(n + 1);
        int maxDepth = 0;
        for (int i = 1; i <= n; i++) {
            level[dist[i]].push_back(i);
            maxDepth = max(maxDepth, dist[i]);
        }

        int lo = 0, hi = maxDepth;
        int bestDepth = 0;
        int endpoint1 = root;

        while (lo <= hi) {
            int mid = (lo + hi) >> 1;
            auto res = ask(level[mid]);
            if (res.second == D) {
                bestDepth = mid;
                endpoint1 = res.first;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        vector<int> dist2(n + 1, -1);
        q = queue<int>();
        dist2[endpoint1] = 0;
        q.push(endpoint1);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) {
                if (dist2[to] != -1) continue;
                dist2[to] = dist2[v] + 1;
                q.push(to);
            }
        }

        vector<int> cand;
        cand.reserve(n);
        for (int i = 1; i <= n; i++) if (dist2[i] == D) cand.push_back(i);

        auto [endpoint2, d2] = ask(cand);

        cout << "! " << endpoint1 << ' ' << endpoint2 << '\n' << flush;

        string verdict;
        cin >> verdict;
        if (verdict != "Correct") return 0;
    }
    return 0;
}