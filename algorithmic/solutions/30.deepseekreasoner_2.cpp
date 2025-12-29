#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

int n;
vector<int> adj[MAXN];
int parent[MAXN], depth[MAXN], sz[MAXN], heavy[MAXN];

void dfs(int u, int p) {
    parent[u] = p;
    depth[u] = depth[p] + 1;
    sz[u] = 1;
    heavy[u] = 0;
    int max_sz = 0;
    for (int v : adj[u]) {
        if (v == p) continue;
        dfs(v, u);
        sz[u] += sz[v];
        if (sz[v] > max_sz) {
            max_sz = sz[v];
            heavy[u] = v;
        }
    }
}

vector<int> get_heavy_path(int u) {
    vector<int> path;
    while (u) {
        path.push_back(u);
        u = heavy[u];
    }
    return path;
}

int query(int x) {
    cout << "? " << x << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

void solve() {
    cin >> n;
    for (int i = 1; i <= n; i++) adj[i].clear();
    for (int i = 0; i < n-1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    dfs(1, 0);
    
    int current = 1;
    while (true) {
        vector<int> path = get_heavy_path(current);
        int len = path.size();
        
        // Exponential search
        int step = 0;
        int last_one = 0;
        bool got_zero = false;
        int zero_idx = -1;
        while (true) {
            int idx = (1 << step);
            if (idx >= len) {
                idx = len - 1;
                int res = query(path[idx]);
                if (res == 1) {
                    last_one = idx;
                } else {
                    got_zero = true;
                    zero_idx = idx;
                }
                break;
            }
            int res = query(path[idx]);
            if (res == 1) {
                last_one = idx;
                step++;
            } else {
                got_zero = true;
                zero_idx = idx;
                break;
            }
        }
        
        // Determine range for binary search
        int l = last_one;
        int r;
        if (got_zero) {
            r = zero_idx - 1;
        } else {
            r = len - 1;
        }
        
        // Binary search
        int best = l;
        while (l <= r) {
            int mid = (l + r + 1) / 2;
            int res = query(path[mid]);
            if (res == 1) {
                best = mid;
                l = mid + 1;
            } else {
                r = mid - 1;
            }
        }
        
        int h = path[best];
        
        // Collect light children of h
        vector<int> lights;
        for (int v : adj[h]) {
            if (v != parent[h] && v != heavy[h]) {
                lights.push_back(v);
            }
        }
        // Sort by subtree size descending
        sort(lights.begin(), lights.end(), [&](int a, int b) {
            return sz[a] > sz[b];
        });
        
        bool found_next = false;
        for (int c : lights) {
            int res = query(c);
            if (res == 1) {
                current = c;
                found_next = true;
                break;
            } else {
                // mole moves to h
                cout << "! " << h << endl;
                cout.flush();
                return;
            }
        }
        
        if (!found_next) {
            // mole is at h
            cout << "! " << h << endl;
            cout.flush();
            return;
        }
        // otherwise continue with new current
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    
    return 0;
}