#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    int x, y;
    char type;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    if (!(cin >> N >> K)) return 0;
    vector<Node> all(N + K);
    for (int i = 0; i < N + K; ++i) {
        string t;
        cin >> all[i].id >> all[i].x >> all[i].y >> t;
        all[i].type = t[0];
    }
    // Collect robots (R and S)
    vector<Node> robots;
    robots.reserve(N);
    for (int i = 0; i < N + K; ++i) {
        if (all[i].type == 'R' || all[i].type == 'S') robots.push_back(all[i]);
    }
    int n = (int)robots.size();
    if (n == 0) {
        // No robots, but per constraints N >= 1. Handle gracefully anyway.
        cout << "#\n\n";
        return 0;
    }
    
    // Prim's algorithm on robots only
    const double INF = 1e300;
    vector<double> best(n, INF);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);
    best[0] = 0.0;
    
    auto edge_cost = [&](int i, int j) -> double {
        long long dx = robots[i].x - robots[j].x;
        long long dy = robots[i].y - robots[j].y;
        long long D = dx*dx + dy*dy;
        bool s_i = (robots[i].type == 'S');
        bool s_j = (robots[j].type == 'S');
        double factor = (s_i || s_j) ? 0.8 : 1.0;
        return factor * (double)D;
    };
    
    for (int it = 0; it < n; ++it) {
        int u = -1;
        double bestVal = INF;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && best[i] < bestVal) {
                bestVal = best[i];
                u = i;
            }
        }
        if (u == -1) break;
        used[u] = 1;
        for (int v = 0; v < n; ++v) {
            if (!used[v]) {
                double w = edge_cost(u, v);
                if (w < best[v]) {
                    best[v] = w;
                    parent[v] = u;
                }
            }
        }
    }
    
    // Output
    // First line: selected relay stations - none
    cout << "#\n";
    
    // Second line: edges of MST among robots
    bool first = true;
    for (int i = 0; i < n; ++i) {
        if (parent[i] != -1) {
            if (!first) cout << "#";
            cout << robots[parent[i]].id << "-" << robots[i].id;
            first = false;
        }
    }
    cout << "\n";
    return 0;
}