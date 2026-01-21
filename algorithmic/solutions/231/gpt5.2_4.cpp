#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    if (!(cin >> n >> m >> T)) return 0;

    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0);

    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        adj[a].push_back(b);
        indeg[b]++;
    }

    // Topological order of the initial DAG
    queue<int> q;
    for (int i = 1; i <= n; i++) if (indeg[i] == 0) q.push(i);

    vector<int> topo;
    topo.reserve(n);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        topo.push_back(u);
        for (int v : adj[u]) {
            if (--indeg[v] == 0) q.push(v);
        }
    }

    if ((int)topo.size() != n) {
        // Should not happen (initial graph is guaranteed to be a DAG)
        return 0;
    }

    long long K = 1LL * n * (n - 1) / 2;
    cout << K << "\n";
    for (int i = 0; i < n; i++) {
        int a = topo[i];
        for (int j = i + 1; j < n; j++) {
            int b = topo[j];
            cout << "+ " << a << " " << b << "\n";
        }
    }
    cout.flush();

    for (int tc = 0; tc < T; tc++) {
        int ansv = -1;
        for (int i = 1; i <= n - 1; i++) {
            cout << "? 1 " << i << "\n";
            cout.flush();

            string res;
            if (!(cin >> res)) return 0;

            if (res == "Lose") {
                ansv = i;
                break;
            }
            // Expected "Win" for all other vertices (graph is acyclic => no "Draw")
        }
        if (ansv == -1) ansv = n;

        cout << "! " << ansv << "\n";
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }

    return 0;
}