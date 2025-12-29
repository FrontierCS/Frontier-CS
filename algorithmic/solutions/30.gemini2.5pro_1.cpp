#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <functional>

using namespace std;

const int LOGN = 13;

int n;
vector<vector<int>> adj;
vector<int> parent;
vector<int> depth;
vector<int> tin, tout;
vector<vector<int>> up;
int timer;
vector<int> subtree_nodes_postorder;

void dfs_precompute(int u, int p, int d) {
    tin[u] = ++timer;
    parent[u] = p;
    depth[u] = d;
    up[u][0] = p;
    for (int i = 1; i < LOGN; ++i) {
        if (up[u][i - 1] != 0) {
            up[u][i] = up[up[u][i - 1]][i - 1];
        } else {
            up[u][i] = 0;
        }
    }
    for (int v : adj[u]) {
        if (v != p) {
            dfs_precompute(v, u, d + 1);
        }
    }
    tout[u] = ++timer;
}

void dfs_postorder(int u, int p) {
    for (int v : adj[u]) {
        if (v != p) {
            dfs_postorder(v, u);
        }
    }
    subtree_nodes_postorder.push_back(u);
}

bool is_ancestor(int u, int v) {
    if (u == 0 || v == 0) return false;
    return tin[u] <= tin[v] && tout[u] >= tout[v];
}

int get_ancestor(int u, int k) {
    k = min(k, depth[u]);
    for (int i = LOGN - 1; i >= 0; --i) {
        if ((k >> i) & 1) {
            u = up[u][i];
        }
    }
    return u;
}

void solve() {
    cin >> n;
    
    adj.assign(n + 1, vector<int>());
    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    parent.assign(n + 1, 0);
    depth.assign(n + 1, 0);
    tin.assign(n + 1, 0);
    tout.assign(n + 1, 0);
    up.assign(n + 1, vector<int>(LOGN, 0));

    timer = 0;
    dfs_precompute(1, 1, 0);
    
    subtree_nodes_postorder.clear();
    dfs_postorder(1, 1);

    vector<int> possible_initial(n);
    iota(possible_initial.begin(), possible_initial.end(), 1);

    int k = 0;

    while (possible_initial.size() > 1) {
        int first_anc = get_ancestor(possible_initial[0], k);
        bool all_same = true;
        for (size_t i = 1; i < possible_initial.size(); ++i) {
            if (get_ancestor(possible_initial[i], k) != first_anc) {
                all_same = false;
                break;
            }
        }

        if (all_same) {
            cout << "! " << first_anc << endl;
            return;
        }

        vector<int> counts(n + 1, 0);
        for (int node : possible_initial) {
            counts[get_ancestor(node, k)]++;
        }

        vector<int> subtree_sum(n + 1, 0);
        for (int u : subtree_nodes_postorder) {
            subtree_sum[u] = counts[u];
            for (int v : adj[u]) {
                if (parent[u] != v) {
                    subtree_sum[u] += subtree_sum[v];
                }
            }
        }
        
        int best_node = -1;
        int min_max_split = n + 1;

        for (int i = 1; i <= n; ++i) {
            int in_subtree_count = subtree_sum[i];
            int out_subtree_count = (int)possible_initial.size() - in_subtree_count;
            int current_max_split = max(in_subtree_count, out_subtree_count);
            
            if (current_max_split < min_max_split) {
                min_max_split = current_max_split;
                best_node = i;
            } else if (current_max_split == min_max_split) {
                if (best_node == -1 || depth[i] < depth[best_node]) {
                    best_node = i;
                }
            }
        }
        
        cout << "? " << best_node << endl;
        int response;
        cin >> response;

        vector<int> next_possible;
        if (response == 1) {
            for (int node : possible_initial) {
                if (is_ancestor(best_node, get_ancestor(node, k))) {
                    next_possible.push_back(node);
                }
            }
        } else { // response == 0
            for (int node : possible_initial) {
                if (!is_ancestor(best_node, get_ancestor(node, k))) {
                    next_possible.push_back(node);
                }
            }
            k++;
        }
        possible_initial = next_possible;
    }

    cout << "! " << get_ancestor(possible_initial[0], k) << endl;
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