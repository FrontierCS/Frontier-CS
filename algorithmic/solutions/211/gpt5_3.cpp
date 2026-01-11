#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) return 0;

    struct Node {
        long long id;
        long long x, y;
        char type;
    };

    vector<Node> robots;
    robots.reserve(N);

    for (int i = 0; i < N + K; ++i) {
        long long id, x, y;
        string t;
        cin >> id >> x >> y >> t;
        char type = t.empty() ? 'R' : t[0];
        if (type == 'R' || type == 'S') {
            robots.push_back({id, x, y, type});
        }
    }

    int n = (int)robots.size();
    if (n == 0) {
        cout << "#\n\n";
        return 0;
    }

    const long long INF = (1LL<<62);
    vector<long long> dist(n, INF);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);

    auto weight = [&](int i, int j) -> long long {
        long long dx = robots[i].x - robots[j].x;
        long long dy = robots[i].y - robots[j].y;
        long long D = dx*dx + dy*dy;
        long long m = (robots[i].type == 'R' && robots[j].type == 'R') ? 5 : 4;
        return m * D;
    };

    dist[0] = 0;
    vector<pair<long long,long long>> edges;
    edges.reserve(n - 1);

    for (int it = 0; it < n; ++it) {
        int u = -1;
        long long best = INF;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && dist[i] < best) {
                best = dist[i];
                u = i;
            }
        }
        if (u == -1) break;
        used[u] = 1;
        if (parent[u] != -1) {
            edges.emplace_back(robots[parent[u]].id, robots[u].id);
        }
        for (int v = 0; v < n; ++v) {
            if (!used[v]) {
                long long w = weight(u, v);
                if (w < dist[v]) {
                    dist[v] = w;
                    parent[v] = u;
                }
            }
        }
    }

    cout << "#\n";
    if (!edges.empty()) {
        cout << edges[0].first << "-" << edges[0].second;
        for (size_t i = 1; i < edges.size(); ++i) {
            cout << "#" << edges[i].first << "-" << edges[i].second;
        }
        cout << "\n";
    } else {
        cout << "\n";
    }

    return 0;
}