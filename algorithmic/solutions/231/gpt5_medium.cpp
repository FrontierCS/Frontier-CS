#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) {
        return 0;
    }

    vector<vector<int>> adj(n);
    vector<int> indeg(n, 0);
    vector<vector<unsigned char>> pres(n, vector<unsigned char>(n, 0));

    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        --a; --b;
        adj[a].push_back(b);
        indeg[b]++;
        pres[a][b] = 1;
    }

    // Topological sort (Kahn's algorithm)
    queue<int> q;
    for (int i = 0; i < n; ++i) if (indeg[i] == 0) q.push(i);
    vector<int> order;
    order.reserve(n);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            if (--indeg[v] == 0) q.push(v);
        }
    }
    // It's guaranteed to be DAG, so order should have size n.

    // Count missing forward edges to make complete DAG along order
    vector<int> pos(n);
    for (int i = 0; i < n; ++i) pos[order[i]] = i;

    long long K = 0;
    for (int i = 0; i < n; ++i) {
        int u = order[i];
        for (int j = i + 1; j < n; ++j) {
            int v = order[j];
            if (!pres[u][v]) ++K;
        }
    }

    cout << K << '\n';
    for (int i = 0; i < n; ++i) {
        int u = order[i];
        for (int j = i + 1; j < n; ++j) {
            int v = order[j];
            if (!pres[u][v]) {
                cout << "+ " << (u + 1) << ' ' << (v + 1) << '\n';
            }
        }
    }
    cout.flush();

    // After modifications, nimber of order[i] = n - 1 - i
    // For nimber x in [0..n-1], the vertex is order[n-1-x]

    for (int t = 0; t < T; ++t) {
        bool found = false;
        // Query for x = 0..n-2
        for (int x = 0; x < n - 1; ++x) {
            int ver = order[n - 1 - x];
            cout << "? 1 " << (ver + 1) << '\n';
            cout.flush();
            string ans;
            if (!(cin >> ans)) return 0;
            if (ans == "Lose") {
                cout << "! " << (ver + 1) << '\n';
                cout.flush();
                string verdict;
                if (!(cin >> verdict)) return 0;
                if (verdict == "Wrong") return 0;
                found = true;
                break;
            } else if (ans == "Draw") {
                // Should not happen in DAG, treat as non-equality
            }
        }
        if (!found) {
            // Last remaining possibility: x = n-1 -> vertex order[0]
            int ver = order[0];
            cout << "! " << (ver + 1) << '\n';
            cout.flush();
            string verdict;
            if (!(cin >> verdict)) return 0;
            if (verdict == "Wrong") return 0;
        }
    }

    return 0;
}