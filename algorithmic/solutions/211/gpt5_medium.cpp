#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long id;
    long long x, y;
    char type; // 'R', 'S'
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<Node> robots;
    robots.reserve(N);
    vector<long long> relay_ids;
    relay_ids.reserve(K);
    
    for (int i = 0; i < N + K; ++i) {
        long long id, x, y;
        string t;
        cin >> id >> x >> y >> t;
        char type = t[0];
        if (type == 'C') {
            relay_ids.push_back(id);
        } else {
            robots.push_back({id, x, y, type});
        }
    }
    
    int n = (int)robots.size();
    // Prim's MST on robots only
    vector<long double> dist(n, numeric_limits<long double>::infinity());
    vector<int> parent(n, -1);
    vector<char> used(n, 0);
    
    if (n > 0) dist[0] = 0.0L;
    
    for (int it = 0; it < n; ++it) {
        int v = -1;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && (v == -1 || dist[i] < dist[v])) v = i;
        }
        if (v == -1) break;
        used[v] = 1;
        for (int u = 0; u < n; ++u) {
            if (used[u]) continue;
            long long dx = robots[v].x - robots[u].x;
            long long dy = robots[v].y - robots[u].y;
            long long D = dx*dx + dy*dy;
            long double factor = ((robots[v].type == 'S') || (robots[u].type == 'S')) ? 0.8L : 1.0L;
            long double w = factor * (long double)D;
            if (w < dist[u]) {
                dist[u] = w;
                parent[u] = v;
            }
        }
    }
    
    // Output selected relays: none
    cout << "#\n";
    // Output edges among robots in MST
    bool first = true;
    for (int i = 0; i < n; ++i) {
        if (parent[i] != -1) {
            if (!first) cout << "#";
            first = false;
            cout << robots[i].id << "-" << robots[parent[i]].id;
        }
    }
    cout << "\n";
    return 0;
}