#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

using namespace std;

const int MAXN = 5005;
const int LOGN = 13;

vector<int> adj[MAXN];
int parent[MAXN][LOGN];
int depth[MAXN];
int tin[MAXN], tout[MAXN];
int timer;
int n;
vector<int> post_order_nodes;

void dfs_precompute(int v, int p, int d) {
    tin[v] = ++timer;
    depth[v] = d;
    parent[v][0] = p;
    for (int i = 1; i < LOGN; ++i) {
        if (parent[v][i-1] != 0) {
            parent[v][i] = parent[parent[v][i-1]][i-1];
        } else {
            parent[v][i] = 0;
        }
    }
    for (int u : adj[v]) {
        if (u != p) {
            dfs_precompute(u, v, d + 1);
        }
    }
    tout[v] = ++timer;
    post_order_nodes.push_back(v);
}

bool is_ancestor(int u, int v) {
    if (u == 0) return true;
    if (v == 0) return false;
    return tin[u] <= tin[v] && tout[u] >= tout[v];
}

int get_ancestor(int u, int k) {
    if (k < 0) return u;
    if (depth[u] <= k) return 1;
    for (int i = 0; i < LOGN; ++i) {
        if ((k >> i) & 1) {
            u = parent[u][i];
        }
    }
    return u;
}

vector<int> sz;
vector<int> current_positions;

void solve() {
    cin >> n;
    for (int i = 0; i <= n; ++i) {
        adj[i].clear();
        for(int j=0; j<LOGN; ++j) parent[i][j] = 0;
    }
    post_order_nodes.clear();

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    timer = 0;
    dfs_precompute(1, 0, 0);

    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    
    int zeros = 0;

    while (p.size() > 1) {
        current_positions.clear();
        current_positions.reserve(p.size());
        for (int u : p) {
            current_positions.push_back(get_ancestor(u, zeros));
        }

        sz.assign(n + 1, 0);
        for(int node : current_positions) {
            sz[node]++;
        }
        for(int u : post_order_nodes) {
            if (parent[u][0] != 0) {
                sz[parent[u][0]] += sz[u];
            }
        }
        
        int best_node = -1;
        int min_max_sz = n + 1;

        for (int i = 1; i <= n; ++i) {
            int current_max_sz = max(sz[i], (int)current_positions.size() - sz[i]);
            if (current_max_sz < min_max_sz) {
                min_max_sz = current_max_sz;
                best_node = i;
            } else if (current_max_sz == min_max_sz) {
                if (depth[i] < depth[best_node]) {
                    best_node = i;
                }
            }
        }
        
        cout << "? " << best_node << endl;
        int response;
        cin >> response;

        vector<int> next_p;
        next_p.reserve(p.size());
        if (response == 1) {
            for (int u : p) {
                if (is_ancestor(best_node, get_ancestor(u, zeros))) {
                    next_p.push_back(u);
                }
            }
        } else {
            for (int u : p) {
                if (!is_ancestor(best_node, get_ancestor(u, zeros))) {
                    next_p.push_back(u);
                }
            }
            zeros++;
        }
        p = next_p;
    }

    cout << "! " << get_ancestor(p[0], zeros) << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}