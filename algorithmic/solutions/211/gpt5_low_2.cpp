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
    if (!(cin >> N >> K)) return 0;
    vector<Device> robots;
    robots.reserve(N);
    vector<int> relays; relays.reserve(K);
    for (int i = 0; i < N + K; ++i) {
        Device d;
        cin >> d.id >> d.x >> d.y >> d.t;
        if (d.t == 'R' || d.t == 'S') robots.push_back(d);
        else if (d.t == 'C') relays.push_back(d.id);
    }
    int n = (int)robots.size();
    vector<double> key(n, numeric_limits<double>::infinity());
    vector<int> parent(n, -1);
    vector<char> inMST(n, 0);
    if (n > 0) key[0] = 0.0;

    auto wfactor = [&](int i, int j) -> double {
        char a = robots[i].t, b = robots[j].t;
        if (a == 'R' && b == 'R') return 1.0;
        return 0.8;
    };
    auto dist2 = [&](int i, int j) -> long long {
        long long dx = (long long)robots[i].x - robots[j].x;
        long long dy = (long long)robots[i].y - robots[j].y;
        return dx*dx + dy*dy;
    };

    for (int it = 0; it < n; ++it) {
        int u = -1;
        double best = numeric_limits<double>::infinity();
        for (int v = 0; v < n; ++v) {
            if (!inMST[v] && key[v] < best) {
                best = key[v];
                u = v;
            }
        }
        if (u == -1) break;
        inMST[u] = 1;
        for (int v = 0; v < n; ++v) {
            if (!inMST[v]) {
                double w = (double)dist2(u, v) * wfactor(u, v);
                if (w < key[v]) {
                    key[v] = w;
                    parent[v] = u;
                }
            }
        }
    }

    // No relay stations used
    cout << "#\n";
    bool first = true;
    for (int i = 0; i < n; ++i) {
        if (parent[i] != -1) {
            if (!first) cout << "#";
            cout << robots[i].id << "-" << robots[parent[i]].id;
            first = false;
        }
    }
    cout << "\n";
    return 0;
}