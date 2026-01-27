#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

struct Solver {
    int n;
    vector<vector<int>> g;

    pair<int,int> ask(const vector<int>& nodes) {
        cout << "? " << nodes.size();
        for (int v : nodes) cout << " " << v;
        cout << endl;
        cout.flush();

        int x, d;
        if (!(cin >> x >> d)) die();
        if (x == -1 && d == -1) die();
        return {x, d};
    }

    vector<vector<int>> bfs_levels(int src, vector<int>& dist) {
        dist.assign(n + 1, -1);
        queue<int> q;
        dist[src] = 0;
        q.push(src);

        vector<vector<int>> levels(1);
        levels[0].push_back(src);

        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) {
                if (dist[to] != -1) continue;
                dist[to] = dist[v] + 1;
                if ((int)levels.size() <= dist[to]) levels.resize(dist[to] + 1);
                levels[dist[to]].push_back(to);
                q.push(to);
            }
        }
        return levels;
    }

    void solve_one() {
        cin >> n;
        g.assign(n + 1, {});
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        vector<int> all(n);
        iota(all.begin(), all.end(), 1);

        auto [x0, D] = ask(all);

        vector<int> dist0;
        auto levels0 = bfs_levels(x0, dist0);
        int maxd0 = (int)levels0.size() - 1;

        int lo = 0, hi = maxd0;
        int bestDist = 0;
        int endpointA = x0;

        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            auto [x, d] = ask(levels0[mid]);
            if (d == D) {
                bestDist = mid;
                endpointA = x;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        vector<int> distA;
        auto levelsA = bfs_levels(endpointA, distA);

        if (D >= (int)levelsA.size() || levelsA[D].empty()) die();

        auto [endpointB, d2] = ask(levelsA[D]);
        if (d2 != D) die();

        cout << "! " << endpointA << " " << endpointB << endl;
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) die();
        if (verdict != "Correct") die();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        Solver s;
        s.solve_one();
    }
    return 0;
}