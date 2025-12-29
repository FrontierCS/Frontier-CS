#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <set>

using namespace std;

const int MAXN = 5005;
vector<int> adj[MAXN];
vector<int> children[MAXN];
int parent[MAXN];
int depth[MAXN];
int tin[MAXN], tout[MAXN], timer;
vector<int> post_order;

void dfs_precompute(int u, int p, int d) {
    parent[u] = p;
    depth[u] = d;
    tin[u] = ++timer;
    if (p != 0) {
        children[p].push_back(u);
    }
    for (int v : adj[u]) {
        if (v != p) {
            dfs_precompute(v, u, d + 1);
        }
    }
    tout[u] = ++timer;
    post_order.push_back(u);
}

bool is_in_subtree(int u, int root) {
    if (root == 0) return true;
    return tin[root] <= tin[u] && tout[u] <= tout[root];
}

void solve() {
    int n;
    cin >> n;

    for (int i = 0; i <= n; ++i) {
        adj[i].clear();
        children[i].clear();
    }

    for (int i = 0; i < n - 1; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    timer = 0;
    post_order.clear();
    dfs_precompute(1, 0, 0);

    vector<int> S(n);
    iota(S.begin(), S.end(), 1);

    while (S.size() > 1) {
        vector<int> s_counts(n + 1, 0);
        vector<bool> is_in_S(n + 1, false);
        for(int node : S) is_in_S[node] = true;

        for (int u : post_order) {
            if (is_in_S[u]) {
                s_counts[u]++;
            }
            for (int v : children[u]) {
                s_counts[u] += s_counts[v];
            }
        }
        
        int best_node = -1;
        double max_score = -1.0;

        for (int u = 1; u <= n; ++u) {
            if (s_counts[u] > 0 && s_counts[u] < S.size()) {
                double balance = min(s_counts[u], (int)S.size() - s_counts[u]);
                double score = balance / (depth[u] + 1.0);
                if (score > max_score) {
                    max_score = score;
                    best_node = u;
                }
            }
        }
        
        if (best_node == -1) {
            best_node = S[0];
        }

        cout << "? " << best_node << endl;
        cout.flush();
        
        int response;
        cin >> response;

        if (response == 1) {
            vector<int> next_S;
            for (int node : S) {
                if (is_in_subtree(node, best_node)) {
                    next_S.push_back(node);
                }
            }
            S = next_S;
        } else {
            set<int> temp_S;
            for (int node : S) {
                if (!is_in_subtree(node, best_node)) {
                    temp_S.insert(parent[node] == 0 ? 1 : parent[node]);
                }
            }
            S.assign(temp_S.begin(), temp_S.end());
        }
    }

    cout << "! " << S[0] << endl;
    cout.flush();
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