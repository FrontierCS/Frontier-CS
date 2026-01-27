#include <bits/stdc++.h>
using namespace std;

struct Device {
    long long id;
    int x, y;
    char type; // 'R' or 'S' (robots), 'C' for relay (ignored)
};

long long sqr(long long x){ return x*x; }

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if(!(cin >> N >> K)) return 0;
    int total = N + K;
    vector<Device> robots;
    robots.reserve(N);
    for (int i = 0; i < total; ++i) {
        long long id; int x, y; string t;
        cin >> id >> x >> y >> t;
        char type = t.empty() ? 'R' : t[0];
        if (type != 'C') {
            robots.push_back({id, x, y, type});
        }
    }
    int n = (int)robots.size();
    // Prim's algorithm on robots only, weights scaled by 5 to avoid floating errors:
    // R-R edge weight = 5 * D, else = 4 * D
    vector<long long> dist(n, LLONG_MAX);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);
    dist[0] = 0;
    for (int it = 0; it < n; ++it) {
        int u = -1;
        long long best = LLONG_MAX;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && dist[i] < best) {
                best = dist[i];
                u = i;
            }
        }
        if (u == -1) break;
        used[u] = 1;
        for (int v = 0; v < n; ++v) {
            if (used[v] || v == u) continue;
            long long dx = (long long)robots[u].x - robots[v].x;
            long long dy = (long long)robots[u].y - robots[v].y;
            long long D = dx*dx + dy*dy;
            int factor = (robots[u].type == 'R' && robots[v].type == 'R') ? 5 : 4;
            long long w = D * factor;
            if (w < dist[v]) {
                dist[v] = w;
                parent[v] = u;
            }
        }
    }

    // Output: no relay stations selected
    cout << "#\n";
    // Output edges
    vector<string> edges;
    edges.reserve(max(0, n-1));
    for (int i = 0; i < n; ++i) {
        if (parent[i] != -1) {
            edges.push_back(to_string(robots[i].id) + "-" + to_string(robots[parent[i]].id));
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