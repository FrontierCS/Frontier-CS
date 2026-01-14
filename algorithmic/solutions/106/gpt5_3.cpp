#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> vals;
    long long t;
    while (cin >> t) vals.push_back(t);
    if (vals.empty()) return 0;
    int n = (int)vals[0];
    vector<long long> rest(vals.begin() + 1, vals.end());
    
    auto all01 = [&](const vector<long long>& a)->bool {
        for (auto x : a) if (!(x == 0 || x == 1)) return false;
        return true;
    };
    auto valid_pairs = [&](const vector<long long>& a)->bool {
        if (a.size() % 2) return false;
        for (size_t i = 0; i + 1 < a.size(); i += 2) {
            long long u = a[i], v = a[i+1];
            if (u < 1 || u > n || v < 1 || v > n) return false;
        }
        return true;
    };
    
    vector<vector<unsigned char>> mat(n+1, vector<unsigned char>(n+1, 0));
    bool built = false;
    
    // Try format: n m (edges list)
    if (!built && rest.size() >= 1) {
        long long m = rest[0];
        if (m >= 0 && 2*m == (long long)rest.size() - 1) {
            bool ok = true;
            for (size_t i = 1; i + 1 < rest.size(); i += 2) {
                long long u = rest[i], v = rest[i+1];
                if (u < 1 || u > n || v < 1 || v > n || u == v) { ok = false; break; }
            }
            if (ok) {
                for (size_t i = 1; i + 1 < rest.size(); i += 2) {
                    int u = (int)rest[i], v = (int)rest[i+1];
                    mat[u][v] = mat[v][u] = 1;
                }
                built = true;
            }
        }
    }
    
    // Try format: n (then adjacency matrix n*n 0/1)
    if (!built && rest.size() == 1LL * n * n && all01(rest)) {
        size_t p = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if (i != j && rest[p]) mat[i][j] = 1;
                ++p;
            }
        }
        built = true;
    }
    
    // Try format: n (then upper triangular adjacency n*(n-1)/2 0/1)
    if (!built && rest.size() == 1LL * n * (n - 1) / 2 && all01(rest)) {
        size_t p = 0;
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                if (rest[p]) mat[i][j] = mat[j][i] = 1;
                ++p;
            }
        }
        built = true;
    }
    
    // Try format: n (then edges list without m)
    if (!built && rest.size() % 2 == 0 && valid_pairs(rest)) {
        for (size_t i = 0; i + 1 < rest.size(); i += 2) {
            int u = (int)rest[i], v = (int)rest[i+1];
            if (u != v) mat[u][v] = mat[v][u] = 1;
        }
        built = true;
    }
    
    // If still not built, assume empty graph (fallback)
    if (!built) {
        // leave mat as all zeros
    }
    
    vector<vector<int>> g(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) if (mat[i][j]) g[i].push_back(j);
    }
    
    vector<int> color(n+1, -1), parent(n+1, -1), depth(n+1, 0);
    auto output_cycle = [&](int u, int v) {
        vector<int> pathU, pathV;
        vector<int> pos(n+1, -1);
        int x = u;
        while (x != -1) {
            pos[x] = (int)pathU.size();
            pathU.push_back(x);
            x = parent[x];
        }
        int lca = -1;
        x = v;
        while (x != -1) {
            if (pos[x] != -1) { lca = x; break; }
            pathV.push_back(x);
            x = parent[x];
        }
        vector<int> cycle;
        // u -> ... -> lca
        for (int i = 0; i <= pos[lca]; ++i) cycle.push_back(pathU[i]);
        // lca -> ... -> v (use reversed pathV)
        for (int i = (int)pathV.size() - 1; i >= 0; --i) cycle.push_back(pathV[i]);
        cout << "N " << cycle.size() << "\n";
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << "\n";
        return;
    };
    
    for (int s = 1; s <= n; ++s) if (color[s] == -1) {
        queue<int> q;
        color[s] = 0; parent[s] = -1; depth[s] = 0;
        q.push(s);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : g[u]) {
                if (color[v] == -1) {
                    color[v] = color[u] ^ 1;
                    parent[v] = u;
                    depth[v] = depth[u] + 1;
                    q.push(v);
                } else if (v != parent[u] && color[v] == color[u]) {
                    output_cycle(u, v);
                    return 0;
                }
            }
        }
    }
    
    vector<int> part;
    for (int i = 1; i <= n; ++i) if (color[i] == 0) part.push_back(i);
    cout << "Y " << part.size() << "\n";
    if (!part.empty()) {
        for (size_t i = 0; i < part.size(); ++i) {
            if (i) cout << ' ';
            cout << part[i];
        }
    }
    cout << "\n";
    return 0;
}