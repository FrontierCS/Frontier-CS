#include <bits/stdc++.h>
using namespace std;

void solve() {
    int n;
    cin >> n;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < n - 1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> F(n + 1);
    for (int i = 1; i <= n; i++) {
        cout << "? 1 1 " << i << endl;
        cout.flush();
        cin >> F[i];
    }

    int total_sum = 0;
    for (int i = 1; i <= n; i++) total_sum += F[i];

    vector<int> candidates;
    for (int r = 1; r <= n; r++) {
        vector<int> parent(n + 1, 0);
        vector<int> order;
        queue<int> q;
        q.push(r);
        parent[r] = -1;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            order.push_back(u);
            for (int v : adj[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                q.push(v);
            }
        }

        vector<int> b(n + 1);
        bool ok = true;
        b[r] = F[r];
        for (int u : order) {
            if (u == r) continue;
            b[u] = F[u] - F[parent[u]];
            if (b[u] != 1 && b[u] != -1) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;

        vector<int> sz(n + 1, 0);
        reverse(order.begin(), order.end());
        for (int u : order) {
            sz[u] = 1;
            for (int v : adj[u]) {
                if (v == parent[u]) continue;
                sz[u] += sz[v];
            }
        }

        int S = 0;
        for (int u : order) {
            S += b[u] * sz[u];
        }
        if (S == total_sum) {
            candidates.push_back(r);
        }
    }

    vector<int> final_b(n + 1);
    if (candidates.size() == 1) {
        int root = candidates[0];
        vector<int> parent(n + 1, 0);
        vector<int> order;
        queue<int> q;
        q.push(root);
        parent[root] = -1;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            order.push_back(u);
            for (int v : adj[u]) {
                if (v == parent[u]) continue;
                parent[v] = u;
                q.push(v);
            }
        }
        final_b[root] = F[root];
        for (int u : order) {
            if (u == root) continue;
            final_b[u] = F[u] - F[parent[u]];
        }
    } else {
        int r0 = candidates[0];
        cout << "? 2 " << r0 << endl;
        cout.flush();
        // no response to read for type 2

        int new_f;
        cout << "? 1 1 " << r0 << endl;
        cout.flush();
        cin >> new_f;

        int real_root = -1;
        for (int r : candidates) {
            vector<int> parent(n + 1, 0);
            vector<int> order;
            queue<int> q;
            q.push(r);
            parent[r] = -1;
            while (!q.empty()) {
                int u = q.front(); q.pop();
                order.push_back(u);
                for (int v : adj[u]) {
                    if (v == parent[u]) continue;
                    parent[v] = u;
                    q.push(v);
                }
            }
            vector<int> b(n + 1);
            b[r] = F[r];
            for (int u : order) {
                if (u == r) continue;
                b[u] = F[u] - F[parent[u]];
            }
            int predicted = F[r0] - 2 * b[r0];
            if (predicted == new_f) {
                real_root = r;
                for (int i = 1; i <= n; i++) final_b[i] = b[i];
                break;
            }
        }
        if (real_root == -1) real_root = candidates[0]; // fallback (should not happen)
        final_b[r0] = -final_b[r0]; // account for the toggle
    }

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << final_b[i];
    cout << endl;
    cout.flush();
}

int main() {
    int t;
    cin >> t;
    while (t--) solve();
    return 0;
}