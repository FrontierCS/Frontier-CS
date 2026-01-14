#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>

void bfs(int n, const std::vector<std::vector<int>>& adj, std::vector<int>& dist, std::queue<int>& q) {
    while (!q.empty()) {
        int u = q.front();
        q.pop();

        for (int v : adj[u]) {
            if (dist[v] == -1) {
                dist[v] = dist[u] + 1;
                q.push(v);
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<int> initial_state(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> initial_state[i];
    }

    std::vector<int> target_state(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> target_state[i];
    }

    std::vector<std::vector<int>> adj(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        std::cin >> u >> v;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    std::vector<int> dist0(n, -1);
    std::vector<int> dist1(n, -1);
    std::queue<int> q0, q1;

    for (int i = 0; i < n; ++i) {
        if (initial_state[i] == 0) {
            dist0[i] = 0;
            q0.push(i);
        } else {
            dist1[i] = 0;
            q1.push(i);
        }
    }

    bfs(n, adj, dist0, q0);
    bfs(n, adj, dist1, q1);

    std::vector<int> T(n);
    int k = 0;
    for (int i = 0; i < n; ++i) {
        if (target_state[i] == 0) {
            T[i] = dist0[i];
        } else {
            T[i] = dist1[i];
        }
        if (T[i] > k) {
            k = T[i];
        }
    }

    std::cout << k << "\n";

    std::vector<std::vector<int>> states(k + 1, std::vector<int>(n));
    states[0] = initial_state;

    for (int t = 1; t <= k; ++t) {
        for (int i = 0; i < n; ++i) {
            if (t >= T[i]) {
                states[t][i] = target_state[i];
            } else {
                states[t][i] = initial_state[i];
            }
        }
    }
    
    for (int t = 0; t <= k; ++t) {
        for (int i = 0; i < n; ++i) {
            std::cout << states[t][i] << (i == n - 1 ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}