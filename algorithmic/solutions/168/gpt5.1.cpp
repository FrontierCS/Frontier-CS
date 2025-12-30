#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;

    vector<int> A(N);
    for (int i = 0; i < N; i++) cin >> A[i];

    vector<vector<int>> g(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    // Read and ignore coordinates
    for (int i = 0; i < N; i++) {
        int x, y;
        cin >> x >> y;
    }

    // Choose BFS root as vertex with minimum beauty value
    int root = 0;
    for (int i = 1; i < N; i++) {
        if (A[i] < A[root]) root = i;
    }

    const int INF = -1;
    vector<int> depth(N, INF), parent(N, -1);

    queue<int> q;
    // BFS from chosen root
    depth[root] = 0;
    parent[root] = -1;
    q.push(root);

    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int to : g[v]) {
            if (depth[to] == INF) {
                depth[to] = depth[v] + 1;
                parent[to] = v;
                q.push(to);
            }
        }
    }

    // In case graph is not connected (though problem says it is)
    for (int i = 0; i < N; i++) {
        if (depth[i] == INF) {
            depth[i] = 0;
            parent[i] = -1;
            q.push(i);
            while (!q.empty()) {
                int v = q.front(); q.pop();
                for (int to : g[v]) {
                    if (depth[to] == INF) {
                        depth[to] = depth[v] + 1;
                        parent[to] = v;
                        q.push(to);
                    }
                }
            }
        }
    }

    int step = H + 1;
    for (int v = 0; v < N; v++) {
        if (depth[v] % step == 0) {
            parent[v] = -1;
        }
    }

    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';

    return 0;
}