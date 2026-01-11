#include <bits/stdc++.h>
using namespace std;

struct Device {
    int id;
    int x, y;
    char t;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }

    vector<Device> robots;
    robots.reserve(N);
    for (int i = 0; i < N + K; ++i) {
        Device d;
        cin >> d.id >> d.x >> d.y >> d.t;
        if (d.t == 'R' || d.t == 'S') {
            robots.push_back(d);
        }
    }

    int n = (int)robots.size();
    if (n == 0) {
        // No robots, no relays or links needed
        cout << "#\n\n";
        return 0;
    }

    const long long INF = (1LL << 62);
    vector<long long> dist(n, INF);
    vector<int> parent(n, -1);
    vector<bool> used(n, false);

    dist[0] = 0;

    for (int iter = 0; iter < n; ++iter) {
        int u = -1;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && (u == -1 || dist[i] < dist[u])) {
                u = i;
            }
        }
        used[u] = true;

        for (int v = 0; v < n; ++v) {
            if (used[v] || v == u) continue;
            long long dx = (long long)robots[u].x - robots[v].x;
            long long dy = (long long)robots[u].y - robots[v].y;
            long long d2 = dx * dx + dy * dy;
            int factor = (robots[u].t == 'S' || robots[v].t == 'S') ? 4 : 5;
            long long w = d2 * factor;
            if (w < dist[v]) {
                dist[v] = w;
                parent[v] = u;
            }
        }
    }

    // First line: no relay stations selected
    cout << "#\n";

    // Second line: communication links of MST
    vector<pair<int,int>> edges;
    edges.reserve(n - 1);
    for (int i = 0; i < n; ++i) {
        if (parent[i] != -1) {
            edges.emplace_back(robots[parent[i]].id, robots[i].id);
        }
    }

    if (!edges.empty()) {
        for (size_t i = 0; i < edges.size(); ++i) {
            if (i) cout << '#';
            cout << edges[i].first << '-' << edges[i].second;
        }
        cout << '\n';
    } else {
        cout << '\n';
    }

    return 0;
}