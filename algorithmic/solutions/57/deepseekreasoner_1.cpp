#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll query_type1_single(int u) {
    cout << "? 1 1 " << u << endl;
    ll res;
    cin >> res;
    return res;
}

void query_type2(int u) {
    cout << "? 2 " << u << endl;
    ll dummy;
    cin >> dummy;
}

ll query_type1_multiple(const vector<int>& nodes) {
    int k = nodes.size();
    cout << "? 1 " << k;
    for (int u : nodes) cout << " " << u;
    cout << endl;
    ll res;
    cin >> res;
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<ll> F(n + 1);
        ll old_S = 0;
        for (int i = 1; i <= n; i++) {
            F[i] = query_type1_single(i);
            old_S += F[i];
        }
        vector<vector<int>> assignments;
        vector<int> roots;
        for (int r = 1; r <= n; r++) {
            vector<int> a(n + 1);
            a[r] = F[r];
            queue<int> q;
            vector<bool> vis(n + 1, false);
            vis[r] = true;
            q.push(r);
            bool valid = true;
            while (!q.empty() && valid) {
                int u = q.front(); q.pop();
                for (int v : adj[u]) {
                    if (!vis[v]) {
                        vis[v] = true;
                        ll diff = F[v] - F[u];
                        if (diff != 1 && diff != -1) {
                            valid = false;
                            break;
                        }
                        a[v] = diff;
                        q.push(v);
                    }
                }
            }
            if (valid) {
                assignments.push_back(a);
                roots.push_back(r);
            }
        }
        if (assignments.size() == 1) {
            cout << "!";
            for (int i = 1; i <= n; i++) cout << " " << assignments[0][i];
            cout << endl;
        } else {
            int v = -1;
            for (int i = 1; i <= n; i++) {
                bool same = true;
                for (size_t j = 1; j < assignments.size(); j++) {
                    if (assignments[j][i] != assignments[0][i]) {
                        same = false;
                        break;
                    }
                }
                if (!same) {
                    v = i;
                    break;
                }
            }
            query_type2(v);
            vector<int> all_nodes;
            for (int i = 1; i <= n; i++) all_nodes.push_back(i);
            ll new_S = query_type1_multiple(all_nodes);
            int correct_idx = -1;
            for (size_t idx = 0; idx < assignments.size(); idx++) {
                int a_v = assignments[idx][v];
                int root = roots[idx];
                vector<int> parent(n + 1);
                vector<vector<int>> children(n + 1);
                queue<int> qq;
                vector<bool> viss(n + 1, false);
                viss[root] = true;
                qq.push(root);
                while (!qq.empty()) {
                    int u = qq.front(); qq.pop();
                    for (int nb : adj[u]) {
                        if (!viss[nb]) {
                            viss[nb] = true;
                            parent[nb] = u;
                            children[u].push_back(nb);
                            qq.push(nb);
                        }
                    }
                }
                function<int(int)> dfs = [&](int u) {
                    int sz = 1;
                    for (int c : children[u]) sz += dfs(c);
                    return sz;
                };
                int sz_v = dfs(v);
                ll expected = old_S - 2LL * a_v * sz_v;
                if (expected == new_S) {
                    correct_idx = idx;
                    break;
                }
            }
            vector<int> final_ans(n + 1);
            for (int i = 1; i <= n; i++) final_ans[i] = assignments[correct_idx][i];
            final_ans[v] = -final_ans[v];
            cout << "!";
            for (int i = 1; i <= n; i++) cout << " " << final_ans[i];
            cout << endl;
        }
    }
    return 0;
}