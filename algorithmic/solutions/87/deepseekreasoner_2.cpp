#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    vector<int> init(n), target(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    for (int i = 0; i < n; ++i) cin >> target[i];

    vector<vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    const int INF = 1e9;
    vector<vector<int>> dist(n, vector<int>(n, INF));
    vector<vector<int>> parent(n, vector<int>(n, -1));

    // BFS from each node to get shortest distances and a parent on a shortest path
    for (int s = 0; s < n; ++s) {
        queue<int> q;
        dist[s][s] = 0;
        parent[s][s] = s;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[s][v] > dist[s][u] + 1) {
                    dist[s][v] = dist[s][u] + 1;
                    parent[s][v] = u;
                    q.push(v);
                } else if (dist[s][v] == dist[s][u] + 1 && parent[s][v] == -1) {
                    parent[s][v] = u;
                }
            }
        }
    }

    // For each node i, find the closest node j with init[j] == target[i]
    vector<int> s_i(n);
    int K = 0;
    for (int i = 0; i < n; ++i) {
        int best_dist = INF, best_j = -1;
        for (int j = 0; j < n; ++j) {
            if (init[j] == target[i] && dist[i][j] < best_dist) {
                best_dist = dist[i][j];
                best_j = j;
            }
        }
        s_i[i] = best_j;
        K = max(K, best_dist);
    }

    // Build the parent function for the transformation
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int s = s_i[i];
        if (i == s) p[i] = i;
        else p[i] = parent[s][i]; // a neighbor closer to s
    }

    // Output the number of steps
    cout << K << '\n';

    // Output the initial state
    for (int i = 0; i < n; ++i) {
        cout << init[i] << " \n"[i == n-1];
    }

    // Simulate K steps
    vector<int> cur = init;
    for (int step = 1; step <= K; ++step) {
        vector<int> nxt(n);
        for (int i = 0; i < n; ++i) {
            nxt[i] = cur[p[i]];
        }
        for (int i = 0; i < n; ++i) {
            cout << nxt[i] << " \n"[i == n-1];
        }
        cur.swap(nxt);
    }

    return 0;
}