#include <bits/stdc++.h>
using namespace std;

int query(const string &s) {
    cout << "? " << s << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
        cin >> n;

        vector<int> deg(n);
        // Query singletons to get degrees
        for (int i = 0; i < n; ++i) {
            string s(n, '0');
            s[i] = '1';
            deg[i] = query(s);
        }

        // Build auxiliary graph H: edge between i,j if they are adjacent
        // or have a common neighbor in original graph.
        vector<vector<int>> adj(n);
        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                string s(n, '0');
                s[i] = s[j] = '1';
                int qij = query(s);
                int t = deg[i] + deg[j] - qij; // t = 2*e_ij + (#common neighbors)
                if (t > 0) {
                    adj[i].push_back(j);
                    adj[j].push_back(i);
                }
            }
        }

        // BFS/DFS on H to check connectivity (same components as original graph)
        vector<int> vis(n, 0);
        queue<int> q;
        vis[0] = 1;
        q.push(0);
        int cnt = 1;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (!vis[v]) {
                    vis[v] = 1;
                    ++cnt;
                    q.push(v);
                }
            }
        }

        int connected = (cnt == n) ? 1 : 0;
        cout << "! " << connected << endl;
        cout.flush();
    }

    return 0;
}