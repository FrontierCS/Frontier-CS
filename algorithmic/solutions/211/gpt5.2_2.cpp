#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id;
    int x, y;
    char type; // 'R','S','C'
};

static inline long long edgeCostScaled(const Node& a, const Node& b) {
    long long dx = (long long)a.x - b.x;
    long long dy = (long long)a.y - b.y;
    long long D = dx * dx + dy * dy;
    // scale by 5: 1.0 -> 5, 0.8 -> 4
    long long factor = (a.type == 'R' && b.type == 'R') ? 5LL : 4LL;
    return D * factor;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;

    vector<Node> robots;
    robots.reserve(N);
    vector<Node> relays;
    relays.reserve(K);

    for (int i = 0; i < N + K; i++) {
        Node node;
        string t;
        cin >> node.id >> node.x >> node.y >> t;
        node.type = t.empty() ? 'R' : t[0];
        if (node.type == 'C') relays.push_back(node);
        else robots.push_back(node);
    }

    // Ensure exactly N robots are considered if input follows constraints; otherwise just use what we got.
    int M = (int)robots.size();
    if (M == 0) {
        cout << "#\n#\n";
        return 0;
    }

    const long long INF = (1LL << 62);
    vector<long long> dist(M, INF);
    vector<int> parent(M, -1);
    vector<char> used(M, 0);

    dist[0] = 0;
    for (int it = 0; it < M; it++) {
        int u = -1;
        long long best = INF;
        for (int i = 0; i < M; i++) {
            if (!used[i] && dist[i] < best) {
                best = dist[i];
                u = i;
            }
        }
        if (u == -1) break; // disconnected (should not happen)
        used[u] = 1;

        for (int v = 0; v < M; v++) {
            if (used[v]) continue;
            long long w = edgeCostScaled(robots[u], robots[v]);
            if (w < dist[v]) {
                dist[v] = w;
                parent[v] = u;
            }
        }
    }

    // No relay stations selected
    cout << "#\n";

    if (M <= 1) {
        cout << "#\n";
        return 0;
    }

    bool first = true;
    for (int i = 1; i < M; i++) {
        int p = parent[i];
        if (p < 0) continue;
        if (!first) cout << "#";
        first = false;
        cout << robots[p].id << "-" << robots[i].id;
    }
    if (first) cout << "#";
    cout << "\n";
    return 0;
}