#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cout.tie(nullptr);

    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n, m;
        cin >> n >> m;
        vector<pair<int, int>> edges(m + 1);
        for (int i = 1; i <= m; ++i) {
            cin >> edges[i].first >> edges[i].second;
        }
        vector<int> status(m + 1, 1); // 1 unblocked
        // Building spanning tree by removal
        int R1 = 10;
        int R2 = 10;
        for (int i = 1; i <= m; ++i) {
            int u = edges[i].first;
            int v = edges[i].second;
            // block i
            cout << "- " << i << endl;
            cout.flush();
            bool is_connected = true;
            // check with y = u
            for (int rep = 0; rep < R1 && is_connected; ++rep) {
                cout << "? 1 " << u << endl;
                cout.flush();
                int reply;
                cin >> reply;
                if (reply == 0) {
                    is_connected = false;
                }
            }
            // check with y = v
            for (int rep = 0; rep < R2 && is_connected; ++rep) {
                cout << "? 1 " << v << endl;
                cout.flush();
                int reply;
                cin >> reply;
                if (reply == 0) {
                    is_connected = false;
                }
            }
            if (!is_connected) {
                // necessary, unblock
                cout << "+ " << i << endl;
                cout.flush();
                status[i] = 1;
            } else {
                // redundant, keep blocked
                status[i] = 0;
            }
        }
        // Now build adj for tree edges
        vector<vector<pair<int, int>>> adj(n + 1);
        for (int i = 1; i <= m; ++i) {
            if (status[i] == 1) {
                int u = edges[i].first, vv = edges[i].second;
                adj[u].emplace_back(vv, i);
                adj[vv].emplace_back(u, i);
            }
        }
        // DFS to compute parent, depth, sub_size, edge_to_parent
        vector<int> parent(n + 1, -1);
        vector<int> depth(n + 1, 0);
        vector<int> sub_size(n + 1, 0);
        vector<int> edge_to_parent(n + 1, 0);
        function<void(int, int, int, int)> dfs = [&](int u, int par, int dep, int par_eid) {
            parent[u] = par;
            depth[u] = dep;
            edge_to_parent[u] = par_eid;
            sub_size[u] = 1;
            for (auto [v, eid] : adj[u]) {
                if (v != par) {
                    dfs(v, u, dep + 1, eid);
                    sub_size[u] += sub_size[v];
                }
            }
        };
        dfs(1, -1, 0, 0);
        // Check if spans all
        if (sub_size[1] != n) {
            // error, but proceed, set all to 1?
            // for simplicity, proceed
        }
        // Now, for each blocked edge, test if repaired
        vector<int> is_repaired(m + 1, 0);
        for (int i = 1; i <= m; ++i) {
            if (status[i] == 1) {
                is_repaired[i] = 1;
            }
        }
        int RR = 20;
        for (int test_i = 1; test_i <= m; ++test_i) {
            if (status[test_i] == 1) continue;
            int a = edges[test_i].first;
            int b = edges[test_i].second;
            // find lca
            int x = a, y = b;
            if (depth[x] > depth[y]) swap(x, y);
            while (depth[y] > depth[x]) {
                y = parent[y];
            }
            if (x == y) {
                int lca = x;
                // path edges
                vector<int> path_edges;
                int cur = a;
                while (cur != lca) {
                    path_edges.push_back(edge_to_parent[cur]);
                    cur = parent[cur];
                }
                cur = b;
                while (cur != lca) {
                    path_edges.push_back(edge_to_parent[cur]);
                    cur = parent[cur];
                }
                // now, compute comp sizes without path_edges
                set<int> blocked_eids(path_edges.begin(), path_edges.end());
                vector<vector<int>> temp_adj(n + 1);
                for (int uu = 1; uu <= n; ++uu) {
                    for (auto [vv, eid] : adj[uu]) {
                        if (blocked_eids.count(eid) == 0) {
                            temp_adj[uu].push_back(vv);
                        }
                    }
                }
                // find components
                vector<bool> visited(n + 1, false);
                vector<int> comp_sz;
                vector<int> comp_id(n + 1, -1);
                int cnum = 0;
                for (int start = 1; start <= n; ++start) {
                    if (!visited[start]) {
                        int sz = 0;
                        stack<int> st;
                        st.push(start);
                        visited[start] = true;
                        comp_id[start] = cnum;
                        while (!st.empty()) {
                            int uu = st.top(); st.pop();
                            ++sz;
                            for (int vv : temp_adj[uu]) {
                                if (!visited[vv]) {
                                    visited[vv] = true;
                                    comp_id[vv] = cnum;
                                    st.push(vv);
                                }
                            }
                        }
                        comp_sz.push_back(sz);
                        ++cnum;
                    }
                }
                // find min comp
                int min_s = n + 1;
                int min_c = -1;
                for (int c = 0; c < cnum; ++c) {
                    if (comp_sz[c] < min_s) {
                        min_s = comp_sz[c];
                        min_c = c;
                    }
                }
                int y_small = -1;
                for (int j = 1; j <= n; ++j) {
                    if (comp_id[j] == min_c) {
                        y_small = j;
                        break;
                    }
                }
                // now test
                // unblock test_i
                cout << "+ " << test_i << endl;
                cout.flush();
                // block path
                for (int eid : path_edges) {
                    cout << "- " << eid << endl;
                    cout.flush();
                }
                // query RR times ?1 y_small
                bool test_connected = true;
                for (int rep = 0; rep < RR && test_connected; ++rep) {
                    cout << "? 1 " << y_small << endl;
                    cout.flush();
                    int reply;
                    cin >> reply;
                    if (reply == 0) {
                        test_connected = false;
                    }
                }
                // restore
                for (int eid : path_edges) {
                    cout << "+ " << eid << endl;
                    cout.flush();
                }
                // block test_i
                cout << "- " << test_i << endl;
                cout.flush();
                if (test_connected) {
                    is_repaired[test_i] = 1;
                } else {
                    is_repaired[test_i] = 0;
                }
            } else {
                // same component? but shouldn't
                is_repaired[test_i] = 0;
            }
        }
        // now output
        cout << "!";
        for (int i = 1; i <= m; ++i) {
            cout << " " << is_repaired[i];
        }
        cout << endl;
        cout.flush();
        int verdict;
        cin >> verdict;
        if (verdict == 0) {
            return 0;
        }
    }
    return 0;
}