#include <bits/stdc++.h>
using namespace std;

static pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int x : nodes) cout << " " << x;
    cout << endl; // flush
    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

static vector<int> bfs_dist(int n, const vector<vector<int>>& g, int src) {
    vector<int> dist(n + 1, -1);
    queue<int> q;
    dist[src] = 0;
    q.push(src);
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int to : g[v]) if (dist[to] == -1) {
            dist[to] = dist[v] + 1;
            q.push(to);
        }
    }
    return dist;
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

        auto [v, L] = ask(all);

        vector<int> distv = bfs_dist(n, g, v);
        int maxDepth = 0;
        for (int i = 1; i <= n; i++) maxDepth = max(maxDepth, distv[i]);

        vector<vector<int>> layers(maxDepth + 1);
        for (int i = 1; i <= n; i++) layers[distv[i]].push_back(i);

        int lo = 0, hi = maxDepth;
        int bestD = 0, endpoint = v;

        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            auto [x, d] = ask(layers[mid]);
            if (d == L) {
                bestD = mid;
                endpoint = x;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        vector<int> distA = bfs_dist(n, g, endpoint);
        vector<int> cand;
        cand.reserve(n);
        for (int i = 1; i <= n; i++) if (distA[i] == L) cand.push_back(i);

        if (cand.empty()) exit(0);

        auto [other, d2] = ask(cand);

        cout << "! " << endpoint << " " << other << endl; // flush

        string verdict;
        if (!(cin >> verdict)) exit(0);
        if (verdict != "Correct") exit(0);
    }

    return 0;
}