#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;

    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];

    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Read and ignore coordinates
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    // Sort vertices by beauty ascending to choose low-beauty vertices as roots
    vector<int> order(N);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int i, int j) {
        return A[i] < A[j];
    });

    const int UNASSIGNED = -2;
    vector<int> parent(N, UNASSIGNED);
    vector<int> depth(N, -1);

    queue<int> q;

    for (int idx = 0; idx < N; ++idx) {
        int r = order[idx];
        if (parent[r] != UNASSIGNED) continue;

        // Start a new tree with root r
        parent[r] = -1;
        depth[r] = 0;
        q.push(r);

        while (!q.empty()) {
            int v = q.front(); q.pop();
            if (depth[v] == H) continue;
            for (int u : adj[v]) {
                if (parent[u] == UNASSIGNED) {
                    parent[u] = v;
                    depth[u] = depth[v] + 1;
                    q.push(u);
                }
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << parent[i];
    }
    cout << '\n';

    return 0;
}