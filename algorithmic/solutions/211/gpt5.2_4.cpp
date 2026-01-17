#include <bits/stdc++.h>
using namespace std;

struct Node {
    string id;
    int x, y;
    char type; // 'R' or 'S'
};

static inline long long wcost(const Node& a, const Node& b) {
    long long dx = (long long)a.x - b.x;
    long long dy = (long long)a.y - b.y;
    long long D = dx * dx + dy * dy;
    // scale by 5: 1.0*D -> 5D, 0.8*D -> 4D
    if (a.type == 'R' && b.type == 'R') return 5LL * D;
    return 4LL * D;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;

    vector<Node> robots;
    robots.reserve(N);

    for (int i = 0; i < N + K; i++) {
        string id;
        int x, y;
        char t;
        cin >> id >> x >> y >> t;
        if (t == 'R' || t == 'S') {
            robots.push_back(Node{id, x, y, t});
        }
    }

    // In case input might not be strictly ordered, ensure we have exactly N robots
    if ((int)robots.size() > N) robots.resize(N);

    cout << "#\n"; // no relay stations used

    if (N <= 1) {
        cout << "#\n";
        return 0;
    }

    const long long INF = (1LL << 62);

    vector<long long> dist(N, INF);
    vector<int> parent(N, -1);
    vector<char> used(N, 0);

    dist[0] = 0;

    for (int it = 0; it < N; it++) {
        int v = -1;
        for (int i = 0; i < N; i++) {
            if (!used[i] && (v == -1 || dist[i] < dist[v])) v = i;
        }
        if (v == -1) break;
        used[v] = 1;

        for (int u = 0; u < N; u++) {
            if (used[u]) continue;
            long long w = wcost(robots[v], robots[u]);
            if (w < dist[u]) {
                dist[u] = w;
                parent[u] = v;
            }
        }
    }

    string links;
    links.reserve((N - 1) * 20);

    bool first = true;
    for (int i = 1; i < N; i++) {
        if (parent[i] < 0) continue;
        if (!first) links.push_back('#');
        first = false;
        links += robots[parent[i]].id;
        links.push_back('-');
        links += robots[i].id;
    }

    if (links.empty()) links = "#";
    cout << links << "\n";

    return 0;
}