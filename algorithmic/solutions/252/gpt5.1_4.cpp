#include <bits/stdc++.h>
using namespace std;

int n;

int query(int u, long long k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();

    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    vector<int> a(n + 1);
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);

    // Reconstruct a[u] for all u
    for (int u = 1; u <= n; ++u) {
        vector<int> cand = all;
        while (cand.size() > 1) {
            int mid = cand.size() / 2;
            vector<int> S(cand.begin(), cand.begin() + mid);
            int ans = query(u, 1, S);
            if (ans == 1) {
                cand.assign(S.begin(), S.end());
            } else {
                cand.erase(cand.begin(), cand.begin() + mid);
            }
        }
        a[u] = cand[0];
    }

    // Build undirected adjacency of the functional graph
    vector<vector<int>> adj(n + 1);
    for (int u = 1; u <= n; ++u) {
        int v = a[u];
        if (u != v) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    // BFS/DFS to find the weakly connected component containing room 1
    vector<int> vis(n + 1, 0);
    vector<int> comp;
    queue<int> q;
    q.push(1);
    vis[1] = 1;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        comp.push_back(u);
        for (int v : adj[u]) {
            if (!vis[v]) {
                vis[v] = 1;
                q.push(v);
            }
        }
    }

    sort(comp.begin(), comp.end());
    cout << "! " << comp.size();
    for (int x : comp) cout << " " << x;
    cout << endl;
    cout.flush();

    return 0;
}