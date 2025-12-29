#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    cin >> n >> m;
    vector<int> A(n + 1), B(n + 1);
    for (int i = 1; i <= n; i++) cin >> A[i];
    for (int i = 1; i <= n; i++) cin >> B[i];
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    vector<int> current(n + 1);
    for (int i = 1; i <= n; i++) current[i] = A[i];
    vector<vector<int>> states;
    vector<int> temp(n);
    for (int i = 1; i <= n; i++) temp[i - 1] = current[i];
    states.push_back(temp);
    int total_steps = 0;
    const int MAX_STEPS = 20000;
    bool all_correct = false;
    while (!all_correct && total_steps < MAX_STEPS) {
        all_correct = true;
        for (int v = 1; v <= n; v++) {
            if (current[v] == B[v]) continue;
            all_correct = false;
            int c = B[v];
            // BFS
            vector<int> dist(n + 1, -1);
            vector<int> parent(n + 1, -1);
            queue<int> q;
            for (int i = 1; i <= n; i++) {
                if (current[i] == c) {
                    dist[i] = 0;
                    parent[i] = -1;
                    q.push(i);
                }
            }
            while (!q.empty()) {
                int u = q.front(); q.pop();
                for (int nei : adj[u]) {
                    if (dist[nei] == -1) {
                        dist[nei] = dist[u] + 1;
                        parent[nei] = u;
                        q.push(nei);
                    }
                }
            }
            if (dist[v] == -1) continue; // should not happen
            int d = dist[v];
            // reconstruct path
            vector<int> p(d + 1);
            int cur_node = v;
            for (int i = d; i >= 0; i--) {
                p[i] = cur_node;
                cur_node = parent[cur_node];
            }
            // perform d steps
            for (int i = 0; i < d; i++) {
                int u = p[i], w = p[i + 1];
                vector<int> next_state(n + 1);
                for (int j = 1; j <= n; j++) {
                    next_state[j] = current[j];
                }
                next_state[w] = current[u];
                if (current[u] != B[u]) {
                    next_state[u] = current[w];
                } else {
                    next_state[u] = current[u];
                }
                // push to states
                vector<int> temp2(n);
                for (int j = 1; j <= n; j++) temp2[j - 1] = next_state[j];
                states.push_back(temp2);
                current = next_state;
                total_steps++;
                if (total_steps >= MAX_STEPS) break;
            }
            if (total_steps >= MAX_STEPS) break;
        }
        if (total_steps >= MAX_STEPS) break;
    }
    // output
    int k = states.size() - 1;
    cout << k << endl;
    for (auto& st : states) {
        for (int i = 0; i < n; i++) {
            cout << st[i];
            if (i < n - 1) cout << " ";
            else cout << endl;
        }
    }
    return 0;
}