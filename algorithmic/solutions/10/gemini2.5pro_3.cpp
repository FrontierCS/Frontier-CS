#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <tuple>

using namespace std;

const int LOGN = 18;

// Use global vectors and resize them for each test case
// because sum of N is limited.
vector<vector<pair<int, int>>> adj;
vector<int> parent;
vector<long long> dist_from_root;
vector<int> depth;
vector<vector<int>> up;

long long query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return d;
}

void solve() {
    int n;
    cin >> n;

    if (n <= 1) {
        cout << "! " << endl;
        return;
    }

    adj.assign(n + 1, vector<pair<int, int>>());
    parent.assign(n + 1, 0);
    dist_from_root.assign(n + 1, 0);
    depth.assign(n + 1, 0);
    up.assign(n + 1, vector<int>(LOGN, 0));

    if (n == 2) {
        long long w = query(1, 2);
        cout << "! 1 2 " << w << endl;
        return;
    }

    long long w12 = query(1, 2);
    
    // Root at 1. Parent of root is 0.
    parent[1] = 0;
    depth[1] = 0;
    dist_from_root[1] = 0;
    
    parent[2] = 1;
    depth[2] = 1;
    dist_from_root[2] = w12;
    adj[1].push_back({2, (int)w12});
    adj[2].push_back({1, (int)w12});

    up[2][0] = 1;
    for (int j = 1; j < LOGN; ++j) {
        up[2][j] = up[up[2][j - 1]][j - 1];
    }

    int a = 1, b = 2;
    long long diam_len = w12;

    for (int i = 3; i <= n; ++i) {
        long long dia = query(i, a);
        long long dib = query(i, b);
        
        long long dist_a_m = (diam_len + dia - dib) / 2;
        
        int u_lca = a, v_lca = b;
        if (depth[u_lca] < depth[v_lca]) swap(u_lca, v_lca);
        
        for (int j = LOGN - 1; j >= 0; --j) {
            if (depth[u_lca] - (1 << j) >= depth[v_lca]) {
                u_lca = up[u_lca][j];
            }
        }

        if (u_lca != v_lca) {
            for (int j = LOGN - 1; j >= 0; --j) {
                if (up[u_lca][j] != 0 && up[u_lca][j] != up[v_lca][j]) {
                    u_lca = up[u_lca][j];
                    v_lca = up[v_lca][j];
                }
            }
            u_lca = parent[u_lca];
        }
        int lca = u_lca;

        long long dist_a_lca = dist_from_root[a] - dist_from_root[lca];
        
        int m;
        if (dist_a_m <= dist_a_lca) {
            int curr = a;
            long long target_dist_from_root = dist_from_root[a] - dist_a_m;
            for (int j = LOGN - 1; j >= 0; --j) {
                if (up[curr][j] != 0 && dist_from_root[up[curr][j]] >= target_dist_from_root) {
                    curr = up[curr][j];
                }
            }
            m = curr;
        } else {
            long long dist_b_m = diam_len - dist_a_m;
            int curr = b;
            long long target_dist_from_root = dist_from_root[b] - dist_b_m;
            for (int j = LOGN - 1; j >= 0; --j) {
                if (up[curr][j] != 0 && dist_from_root[up[curr][j]] >= target_dist_from_root) {
                    curr = up[curr][j];
                }
            }
            m = curr;
        }
        
        long long w_im = dia - dist_a_m;
        adj[i].push_back({m, (int)w_im});
        adj[m].push_back({i, (int)w_im});

        parent[i] = m;
        depth[i] = depth[m] + 1;
        dist_from_root[i] = dist_from_root[m] + w_im;

        up[i][0] = m;
        for (int j = 1; j < LOGN; ++j) {
            up[i][j] = up[up[i][j - 1]][j - 1];
            if(up[i][j] == 0) break;
        }

        if (dia > diam_len) {
            diam_len = dia;
            b = i;
        }
        if (dib > diam_len) {
            diam_len = dib;
            a = i;
        }
    }

    cout << "! ";
    vector<tuple<int, int, int>> edges;
    for (int u = 1; u <= n; ++u) {
        for (auto& edge : adj[u]) {
            int v = edge.first;
            int w = edge.second;
            if (u < v) {
                edges.emplace_back(u, v, w);
            }
        }
    }
    for(size_t i = 0; i < edges.size(); ++i) {
        cout << get<0>(edges[i]) << " " << get<1>(edges[i]) << " " << get<2>(edges[i]) << (i == edges.size() - 1 ? "" : " ");
    }
    cout << endl;
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