#include <bits/stdc++.h>
using namespace std;

struct Device {
    long long id;
    long long x, y;
    char type; // 'R', 'S', or 'C'
    bool isS() const { return type == 'S'; }
};

long long sqDist(const Device& a, const Device& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return dx * dx + dy * dy;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) {
        return 0;
    }

    vector<Device> robots;
    robots.reserve(N);
    // We can ignore relay stations for baseline MST
    for (int i = 0; i < N + K; ++i) {
        Device d;
        cin >> d.id >> d.x >> d.y >> d.type;
        if (d.type == 'R' || d.type == 'S') {
            robots.push_back(d);
        }
    }

    int n = (int)robots.size();
    vector<int> parent(n, -1);
    vector<char> used(n, 0);
    const long long INF = (1LL<<62);
    vector<long long> dist(n, INF);

    if (n > 0) {
        dist[0] = 0;
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

            for (int v = 0; v < n; ++v) {
                if (used[v]) continue;
                long long D = sqDist(robots[u], robots[v]);
                // Scale costs by 5 to avoid floating comparisons:
                // R-R: 5*D, any S involved: 4*D
                long long factor = (robots[u].isS() || robots[v].isS()) ? 4 : 5;
                long long w = D * factor;
                if (w < dist[v]) {
                    dist[v] = w;
                    parent[v] = u;
                }
            }
        }
    }

    // First line: selected relay stations. None used -> print "#"
    cout << "#\n";

    // Second line: MST edges among robots
    if (n <= 1) {
        cout << "#\n";
    } else {
        bool first = true;
        for (int i = 0; i < n; ++i) {
            if (parent[i] != -1) {
                if (!first) cout << "#";
                first = false;
                cout << robots[parent[i]].id << "-" << robots[i].id;
            }
        }
        if (first) {
            // No edges (shouldn't happen when n>1), but handle gracefully
            cout << "#";
        }
        cout << "\n";
    }

    return 0;
}