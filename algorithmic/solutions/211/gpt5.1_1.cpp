#include <bits/stdc++.h>
using namespace std;

struct Robot {
    int id;
    int x, y;
    char type;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;

    vector<Robot> robots;
    robots.reserve(N);
    for (int i = 0; i < N + K; ++i) {
        int id, x, y;
        string s;
        cin >> id >> x >> y >> s;
        char t = s[0];
        if (t != 'C') {
            robots.push_back({id, x, y, t});
        }
    }

    int Rnum = (int)robots.size();
    if (Rnum == 0) {
        cout << "#\n#\n";
        return 0;
    }

    const double INF = 1e100;
    vector<double> dist(Rnum, INF);
    vector<int> parent(Rnum, -1);
    vector<char> used(Rnum, 0);

    dist[0] = 0.0;

    for (int i = 0; i < Rnum; ++i) {
        int u = -1;
        double best = INF;
        for (int j = 0; j < Rnum; ++j) {
            if (!used[j] && dist[j] < best) {
                best = dist[j];
                u = j;
            }
        }
        if (u == -1) break;
        used[u] = 1;

        for (int v = 0; v < Rnum; ++v) {
            if (used[v]) continue;
            long long dx = (long long)robots[u].x - robots[v].x;
            long long dy = (long long)robots[u].y - robots[v].y;
            double D = (double)(dx * dx + dy * dy);
            double coef = (robots[u].type == 'S' || robots[v].type == 'S') ? 0.8 : 1.0;
            double w = D * coef;
            if (w < dist[v]) {
                dist[v] = w;
                parent[v] = u;
            }
        }
    }

    vector<pair<int, int>> edges;
    edges.reserve(max(0, Rnum - 1));
    for (int i = 0; i < Rnum; ++i) {
        if (parent[i] != -1) {
            edges.push_back({robots[parent[i]].id, robots[i].id});
        }
    }

    // No relay stations used
    cout << "#\n";

    if (edges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < edges.size(); ++i) {
            if (i) cout << '#';
            cout << edges[i].first << '-' << edges[i].second;
        }
        cout << '\n';
    }

    return 0;
}