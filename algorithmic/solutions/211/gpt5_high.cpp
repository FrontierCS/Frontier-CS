#include <bits/stdc++.h>
using namespace std;

struct Device {
    int id;
    long long x, y;
    char type;
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
        int id; long long x, y; string t;
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
    
    const double INF = numeric_limits<double>::infinity();
    vector<double> minDist(n, INF);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);
    minDist[0] = 0.0;
    
    auto weight = [&](int i, int j) -> double {
        long long dx = robots[i].x - robots[j].x;
        long long dy = robots[i].y - robots[j].y;
        long long Dll = dx*dx + dy*dy;
        double D = (double)Dll;
        double factor = (robots[i].type == 'S' || robots[j].type == 'S') ? 0.8 : 1.0;
        return D * factor;
    };
    
    for (int it = 0; it < n; ++it) {
        int u = -1;
        double best = INF;
        for (int i = 0; i < n; ++i) {
            if (!used[i] && minDist[i] < best) {
                best = minDist[i];
                u = i;
            }
        }
        if (u == -1) break;
        used[u] = 1;
        for (int v = 0; v < n; ++v) {
            if (!used[v]) {
                double w = weight(u, v);
                if (w < minDist[v]) {
                    minDist[v] = w;
                    parent[v] = u;
                }
            }
        }
    }
    
    cout << "#\n";
    bool first = true;
    for (int i = 1; i < n; ++i) {
        if (parent[i] == -1) continue;
        if (!first) cout << "#";
        cout << robots[i].id << "-" << robots[parent[i]].id;
        first = false;
    }
    cout << "\n";
    
    return 0;
}