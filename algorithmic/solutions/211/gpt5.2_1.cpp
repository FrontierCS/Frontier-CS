#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long id;
    int x, y;
    char type; // 'R' or 'S'
};

static inline long long weightScaled5(const Node& a, const Node& b) {
    long long dx = (long long)a.x - b.x;
    long long dy = (long long)a.y - b.y;
    long long D = dx * dx + dy * dy;
    // 1.0 * D -> 5*D, 0.8 * D -> 4*D
    return (a.type == 'S' || b.type == 'S') ? (4LL * D) : (5LL * D);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, K;
    if (!(cin >> N >> K)) return 0;

    vector<Node> robots;
    robots.reserve(N);

    for (int i = 0; i < N + K; i++) {
        long long id;
        int x, y;
        char type;
        cin >> id >> x >> y >> type;
        if (type == 'R' || type == 'S') {
            robots.push_back(Node{id, x, y, type});
        }
        // type 'C' relays ignored in this solution
    }

    int n = (int)robots.size();
    if (n == 0) {
        cout << "#\n#\n";
        return 0;
    }

    const long long INF = (1LL << 62);
    vector<long long> best(n, INF);
    vector<int> parent(n, -1);
    vector<char> used(n, 0);

    best[0] = 0;

    for (int it = 0; it < n; it++) {
        int v = -1;
        long long bv = INF;
        for (int i = 0; i < n; i++) {
            if (!used[i] && best[i] < bv) {
                bv = best[i];
                v = i;
            }
        }
        if (v == -1) break;
        used[v] = 1;

        for (int u = 0; u < n; u++) {
            if (used[u]) continue;
            long long w = weightScaled5(robots[v], robots[u]);
            if (w < best[u]) {
                best[u] = w;
                parent[u] = v;
            }
        }
    }

    cout << "#\n";

    if (n == 1) {
        cout << "#\n";
        return 0;
    }

    vector<string> edges;
    edges.reserve(n - 1);
    for (int i = 1; i < n; i++) {
        int p = parent[i];
        if (p < 0) continue; // should not happen
        edges.push_back(to_string(robots[p].id) + "-" + to_string(robots[i].id));
    }

    if (edges.empty()) {
        cout << "#\n";
    } else {
        for (size_t i = 0; i < edges.size(); i++) {
            if (i) cout << "#";
            cout << edges[i];
        }
        cout << "\n";
    }

    return 0;
}