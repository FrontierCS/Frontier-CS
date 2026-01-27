#include <bits/stdc++.h>
using namespace std;

static pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int v : nodes) cout << ' ' << v;
    cout << '\n';
    cout.flush();

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
        int u = q.front(); q.pop();
        for (int v : g[u]) if (dist[v] == -1) {
            dist[v] = dist[u] + 1;
            q.push(v);
        }
    }
    return dist;
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
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto [x0, D] = ask(all);

        auto dist0 = bfs_dist(n, g, x0);
        int maxdist = 0;
        for (int i = 1; i <= n; i++) maxdist = max(maxdist, dist0[i]);

        vector<vector<int>> buckets(maxdist + 1);
        for (int i = 1; i <= n; i++) buckets[dist0[i]].push_back(i);

        int lo = 0, hi = maxdist;
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            if (buckets[mid].empty()) {
                hi = mid - 1;
                continue;
            }
            auto [xm, dm] = ask(buckets[mid]);
            if (dm == D) lo = mid;
            else hi = mid - 1;
        }
        int L1 = lo;

        int p;
        {
            auto [xp, dp] = ask(buckets[L1]);
            p = xp;
        }

        auto distp = bfs_dist(n, g, p);
        vector<int> layerD;
        layerD.reserve(n);
        for (int i = 1; i <= n; i++) if (distp[i] == D) layerD.push_back(i);

        int q;
        {
            auto [xq, dq] = ask(layerD);
            q = xq;
        }

        cout << "! " << p << ' ' << q << '\n';
        cout.flush();

        string verdict;
        cin >> verdict;
        if (verdict != "Correct") return 0;
    }
    return 0;
}