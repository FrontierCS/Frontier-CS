#include <bits/stdc++.h>
using namespace std;

static pair<int,int> ask(const vector<int>& nodes) {
    cout << "? " << (int)nodes.size();
    for (int v : nodes) cout << " " << v;
    cout << endl;
    cout.flush();

    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

static vector<vector<int>> buildLayers(const vector<vector<int>>& g, int start, vector<int>& dist) {
    int n = (int)g.size() - 1;
    dist.assign(n + 1, -1);
    queue<int> q;
    dist[start] = 0;
    q.push(start);
    int mx = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        mx = max(mx, dist[u]);
        for (int v : g[u]) {
            if (dist[v] != -1) continue;
            dist[v] = dist[u] + 1;
            q.push(v);
        }
    }
    vector<vector<int>> layers(mx + 1);
    for (int i = 1; i <= n; i++) layers[dist[i]].push_back(i);
    return layers;
}

static void solveCase(int n, const vector<vector<int>>& g) {
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);

    auto [x, d] = ask(all); // x is on path(s,f), d = dist(s,f)

    vector<int> distX;
    auto layersX = buildLayers(g, x, distX);
    int maxdist = (int)layersX.size() - 1;

    int hi = min(maxdist, d);
    int lo = 0, endpoint = x;

    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        auto [node, sum] = ask(layersX[mid]);
        if (sum == d) {
            lo = mid;
            endpoint = node;
        } else {
            hi = mid - 1;
        }
    }

    // Ensure endpoint corresponds to the farthest valid layer
    endpoint = ask(layersX[lo]).first;

    vector<int> distE;
    auto layersE = buildLayers(g, endpoint, distE);

    if (d >= (int)layersE.size() || layersE[d].empty()) exit(0); // should not happen
    int other = ask(layersE[d]).first;

    cout << "! " << endpoint << " " << other << endl;
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
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }
        solveCase(n, g);
    }
    return 0;
}