#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // Query all nodes to get m and D
        cout << "? " << n;
        for (int i = 1; i <= n; ++i) {
            cout << " " << i;
        }
        cout << endl;
        cout.flush();
        int m, D;
        cin >> m >> D;
        if (m == -1) {
            return 0;
        }
        // BFS from m to compute dist and root_child
        vector<int> dist(n + 1, -1);
        vector<int> root_child(n + 1, 0);
        vector<bool> vis(n + 1, false);
        queue<int> q;
        q.push(m);
        vis[m] = true;
        dist[m] = 0;
        root_child[m] = 0;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (!vis[v]) {
                    vis[v] = true;
                    dist[v] = dist[u] + 1;
                    root_child[v] = (u == m ? v : root_child[u]);
                    q.push(v);
                }
            }
        }
        // Query all except m to get x and c1
        vector<int> query_set;
        for (int i = 1; i <= n; ++i) {
            if (i != m) {
                query_set.push_back(i);
            }
        }
        cout << "? " << query_set.size();
        for (int v : query_set) {
            cout << " " << v;
        }
        cout << endl;
        cout.flush();
        int x, dx;
        cin >> x >> dx;
        if (x == -1) {
            return 0;
        }
        int c1 = root_child[x];
        // Query all except m and subtree c1 to check for second arm
        vector<int> query_set2;
        for (int i = 1; i <= n; ++i) {
            if (i == m) continue;
            if (root_child[i] == c1) continue;
            query_set2.push_back(i);
        }
        bool has_second = false;
        int c2 = 0;
        int y = -1;
        if (!query_set2.empty()) {
            cout << "? " << query_set2.size();
            for (int v : query_set2) {
                cout << " " << v;
            }
            cout << endl;
            cout.flush();
            int yy, dy;
            cin >> yy >> dy;
            if (yy == -1) {
                return 0;
            }
            if (dy == D) {
                has_second = true;
                c2 = root_child[yy];
                y = yy;
            }
        }
        // Function to find endpoint for a given c
        auto find_endpoint = [&](int cc) -> int {
            // Binary search for max k
            int low = 1, high = n;
            int maxk = 0;
            while (low <= high) {
                int mid = (low + high) / 2;
                vector<int> sset;
                for (int v = 1; v <= n; ++v) {
                    if (root_child[v] == cc && dist[v] >= mid) {
                        sset.push_back(v);
                    }
                }
                if (sset.empty()) {
                    high = mid - 1;
                    continue;
                }
                cout << "? " << sset.size();
                for (int v : sset) {
                    cout << " " << v;
                }
                cout << endl;
                cout.flush();
                int z, dz;
                cin >> z >> dz;
                if (z == -1) {
                    return 0; // terminate
                }
                if (dz == D) {
                    maxk = mid;
                    low = mid + 1;
                } else {
                    high = mid - 1;
                }
            }
            int L = maxk;
            // Query level L
            vector<int> level;
            for (int v = 1; v <= n; ++v) {
                if (root_child[v] == cc && dist[v] == L) {
                    level.push_back(v);
                }
            }
            cout << "? " << level.size();
            for (int v : level) {
                cout << " " << v;
            }
            cout << endl;
            cout.flush();
            int e, de;
            cin >> e >> de;
            if (e == -1) {
                return 0; // terminate
            }
            return e;
        };
        int hidden1, hidden2;
        if (!has_second) {
            hidden1 = m;
            hidden2 = find_endpoint(c1);
        } else {
            hidden1 = find_endpoint(c1);
            hidden2 = find_endpoint(c2);
        }
        // Output the answer
        cout << "! " << hidden1 << " " << hidden2 << endl;
        cout.flush();
        string resp;
        cin >> resp;
        if (resp != "Correct") {
            return 0;
        }
    }
    return 0;
}