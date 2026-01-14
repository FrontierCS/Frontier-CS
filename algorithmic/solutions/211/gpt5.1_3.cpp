#include <bits/stdc++.h>
using namespace std;

struct Device {
    string id;
    int x, y;
    char type; // 'R' or 'S'
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }

    int total = N + K;
    vector<Device> robots;

    for (int i = 0; i < total; ++i) {
        string id;
        int x, y;
        char t;
        cin >> id >> x >> y >> t;
        if (t == 'R' || t == 'S') {
            robots.push_back({id, x, y, t});
        }
        // ignore relay stations ('C') for MST construction
    }

    int M = (int)robots.size();
    if (M == 0) {
        // No robots (should not happen per constraints), but output empty solution
        cout << "#\n#\n";
        return 0;
    }

    const double INF = 1e100;
    vector<double> minDist(M, INF);
    vector<int> parent(M, -1);
    vector<bool> used(M, false);

    minDist[0] = 0.0;

    for (int i = 0; i < M; ++i) {
        int u = -1;
        double best = INF;
        for (int j = 0; j < M; ++j) {
            if (!used[j] && minDist[j] < best) {
                best = minDist[j];
                u = j;
            }
        }
        if (u == -1) break;
        used[u] = true;

        for (int v = 0; v < M; ++v) {
            if (used[v]) continue;
            double dx = (double)robots[u].x - (double)robots[v].x;
            double dy = (double)robots[u].y - (double)robots[v].y;
            double D = dx * dx + dy * dy;
            double w;
            if (robots[u].type == 'R' && robots[v].type == 'R') {
                w = D;
            } else {
                w = 0.8 * D;
            }
            if (w < minDist[v]) {
                minDist[v] = w;
                parent[v] = u;
            }
        }
    }

    // First line: no relay stations used
    cout << "#\n";

    // Second line: communication links (MST edges)
    vector<string> edges;
    for (int i = 1; i < M; ++i) {
        if (parent[i] != -1) {
            string e = robots[parent[i]].id + "-" + robots[i].id;
            edges.push_back(e);
        }
    }

    if (edges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < edges.size(); ++i) {
            if (i) cout << "#";
            cout << edges[i];
        }
        cout << "\n";
    }

    return 0;
}