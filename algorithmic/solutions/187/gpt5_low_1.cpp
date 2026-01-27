#include <bits/stdc++.h>
using namespace std;

struct Node {
    int sat, deg, idx;
};
struct Cmp {
    bool operator()(const Node& a, const Node& b) const {
        if (a.sat != b.sat) return a.sat < b.sat;          // higher sat first
        if (a.deg != b.deg) return a.deg < b.deg;          // higher degree first
        return a.idx > b.idx;                               // lower index first
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<char>> adj(N, vector<char>(N, 0));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        adj[u][v] = adj[v][u] = 1;
    }

    // Build complement graph
    vector<vector<int>> compNbrs(N);
    vector<int> degComp(N, 0);
    for (int u = 0; u < N; ++u) {
        for (int v = 0; v < N; ++v) {
            if (u == v) continue;
            if (!adj[u][v]) {
                compNbrs[u].push_back(v);
            }
        }
        degComp[u] = (int)compNbrs[u].size();
    }

    vector<int> color(N, 0);
    vector<int> sat(N, 0);
    // For DSATUR, track which colors are present among complement neighbors
    vector<vector<char>> neighColorPresent(N, vector<char>(N + 1, 0));

    priority_queue<Node, vector<Node>, Cmp> pq;
    for (int i = 0; i < N; ++i) {
        pq.push({0, degComp[i], i});
    }

    int Kused = 0;
    int coloredCount = 0;

    while (coloredCount < N) {
        Node cur;
        // Extract a valid top
        while (true) {
            cur = pq.top(); pq.pop();
            if (color[cur.idx] == 0 && sat[cur.idx] == cur.sat) break;
            if (pq.empty()) break;
        }
        int u = cur.idx;
        // Choose smallest available color
        int c = 1;
        for (; c <= Kused; ++c) {
            if (!neighColorPresent[u][c]) break;
        }
        if (c == Kused + 1) {
            Kused++;
        }
        color[u] = c;
        coloredCount++;

        // Update neighbors' saturation
        for (int v : compNbrs[u]) {
            if (color[v] == 0) {
                if (!neighColorPresent[v][c]) {
                    neighColorPresent[v][c] = 1;
                    sat[v]++;
                }
                pq.push({sat[v], degComp[v], v});
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }
    return 0;
}