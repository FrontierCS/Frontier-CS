#include <bits/stdc++.h>

using namespace std;

bool find_path(int pos, vector<int>& path, const vector<vector<int>>& adj, vector<bool>& used, int n) {
    if (pos == n) return true;
    int u = path[pos - 1];
    for (int v : adj[u]) {
        if (!used[v]) {
            used[v] = true;
            path[pos] = v;
            if (find_path(pos + 1, path, adj, used, n)) return true;
            used[v] = false;
        }
    }
    return false;
}

bool find_sub(int pos, vector<int>& subpath, const vector<vector<int>>& adj, vector<bool>& used, int n, int target, int forbidden) {
    if (pos == n - 1) return subpath[pos - 1] == target;
    int u = subpath[pos - 1];
    for (int v : adj[u]) {
        if (v != forbidden && !used[v]) {
            used[v] = true;
            subpath[pos] = v;
            if (find_sub(pos + 1, subpath, adj, used, n, target, forbidden)) return true;
            used[v] = false;
        }
    }
    return false;
}

bool is_connected(const vector<vector<int>>& adj, int n) {
    vector<bool> visited(n, false);
    queue<int> q;
    q.push(0);
    visited[0] = true;
    int count = 1;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        for (int v : adj[u]) if (!visited[v]) {
            visited[v] = true;
            q.push(v);
            count++;
        }
    }
    return count == n;
}

int main() {
    int n;
    while (cin >> n) {
        vector<vector<int>> C(n, vector<int>(n));
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                cin >> C[i][j];
            }
        }
        vector<vector<int>> adj0(n), adj1(n);
        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (C[i][j] == 0) {
                    adj0[i].push_back(j);
                    adj0[j].push_back(i);
                } else {
                    adj1[i].push_back(j);
                    adj1[j].push_back(i);
                }
            }
        }
        for (int i = 0; i < n; i++) {
            sort(adj0[i].begin(), adj0[i].end());
            sort(adj1[i].begin(), adj1[i].end());
        }
        vector<int> path(n);
        vector<bool> used(n);
        bool found = false;
        vector<int> result(n, -1);
        // try mono G0
        if (is_connected(adj0, n)) {
            used.assign(n, false);
            used[0] = true;
            path[0] = 0;
            if (find_path(1, path, adj0, used, n)) {
                found = true;
                for (int i = 0; i < n; i++) result[i] = path[i];
            }
        }
        // try mono G1
        if (!found && is_connected(adj1, n)) {
            used.assign(n, false);
            used[0] = true;
            path[0] = 0;
            if (find_path(1, path, adj1, used, n)) {
                found = true;
                for (int i = 0; i < n; i++) result[i] = path[i];
            }
        }
        // try insert for G0
        if (!found && is_connected(adj0, n)) {
            vector<int> deg(n);
            for (int i = 0; i < n; i++) deg[i] = adj0[i].size();
            int maxd = -1, v = -1;
            for (int i = 0; i < n; i++) if (deg[i] > maxd) {
                maxd = deg[i];
                v = i;
            }
            if (maxd >= 2) {
                int short_color = 0;
                int a = 0;
                while (a < n && (a == v || C[v][a] != short_color)) a++;
                if (a < n) {
                    int b = 0;
                    while (b < n && (b == v || b == a || C[v][b] != short_color)) b++;
                    if (b < n) {
                        vector<int> subpath(n - 1);
                        used.assign(n, false);
                        used[v] = true;
                        used[b] = true;
                        subpath[0] = b;
                        if (find_sub(1, subpath, adj1, used, n, a, v)) {
                            result[0] = a;
                            result[1] = v;
                            result[2] = b;
                            for (int i = 3; i < n; i++) {
                                result[i] = subpath[i - 2];
                            }
                            found = true;
                        }
                    }
                }
            }
        }
        // try insert for G1
        if (!found && is_connected(adj1, n)) {
            vector<int> deg(n);
            for (int i = 0; i < n; i++) deg[i] = adj1[i].size();
            int maxd = -1, v = -1;
            for (int i = 0; i < n; i++) if (deg[i] > maxd) {
                maxd = deg[i];
                v = i;
            }
            if (maxd >= 2) {
                int short_color = 1;
                int a = 0;
                while (a < n && (a == v || C[v][a] != short_color)) a++;
                if (a < n) {
                    int b = 0;
                    while (b < n && (b == v || b == a || C[v][b] != short_color)) b++;
                    if (b < n) {
                        vector<int> subpath(n - 1);
                        used.assign(n, false);
                        used[v] = true;
                        used[b] = true;
                        subpath[0] = b;
                        if (find_sub(1, subpath, adj0, used, n, a, v)) {
                            result[0] = a;
                            result[1] = v;
                            result[2] = b;
                            for (int i = 3; i < n; i++) {
                                result[i] = subpath[i - 2];
                            }
                            found = true;
                        }
                    }
                }
            }
        }
        if (found) {
            for (int i = 0; i < n; i++) {
                if (i > 0) cout << " ";
                cout << result[i] + 1;
            }
            cout << endl;
        } else {
            cout << -1 << endl;
        }
    }
    return 0;
}