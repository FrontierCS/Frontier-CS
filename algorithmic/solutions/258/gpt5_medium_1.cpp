#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> g;

pair<int,int> query(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int v : nodes) cout << " " << v;
    cout << endl;
    cout.flush();
    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

vector<int> bfs(int start) {
    vector<int> dist(n + 1, -1);
    queue<int> q;
    dist[start] = 0;
    q.push(start);
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
        cin >> n;
        g.assign(n + 1, {});
        for (int i = 0; i < n - 1; ++i) {
            int u, v; cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto rD = query(all);
        int r = rD.first;
        int D = rD.second;

        vector<int> distR = bfs(r);
        int depthMax = 0;
        for (int i = 1; i <= n; ++i) depthMax = max(depthMax, distR[i]);

        int lo = 0, hi = depthMax;
        int best = r;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            vector<int> cand;
            cand.reserve(n);
            for (int i = 1; i <= n; ++i) if (distR[i] == mid) cand.push_back(i);
            if (cand.empty()) { // should not happen for 0..depthMax in a tree, but safe-guard
                hi = mid - 1;
                continue;
            }
            auto res = query(cand);
            if (res.second == D) {
                best = res.first;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        vector<int> distBest = bfs(best);
        vector<int> cand2;
        for (int i = 1; i <= n; ++i) if (distBest[i] == D) cand2.push_back(i);
        auto other = query(cand2);
        int endpoint2 = other.first;

        cout << "! " << best << " " << endpoint2 << endl;
        cout.flush();
        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }

    return 0;
}