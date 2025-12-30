#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<int> a(10);
    for (int i = 0; i < 10; i++) cin >> a[i];
    vector<vector<int>> adj(n + 1), rev(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        rev[v].push_back(u);
    }
    vector<int> outdeg(n + 1);
    for (int i = 1; i <= n; i++) outdeg[i] = adj[i].size();
    for (int i = 1; i <= n; i++) {
        sort(adj[i].begin(), adj[i].end(), [&](int x, int y) {
            if (outdeg[x] != outdeg[y]) return outdeg[x] < outdeg[y];
            return x < y;
        });
    }
    vector<bool> vis(n + 1, false);
    stack<int> order;
    function<void(int)> dfs1 = [&](int u) {
        vis[u] = true;
        for (int v : adj[u]) if (!vis[v]) dfs1(v);
        order.push(u);
    };
    for (int i = 1; i <= n; i++) if (!vis[i]) dfs1(i);
    fill(vis.begin(), vis.end(), false);
    vector<int> scc(n + 1, -1);
    int scc_cnt = 0;
    function<void(int, int)> dfs2 = [&](int u, int id) {
        vis[u] = true;
        scc[u] = id;
        for (int v : rev[u]) if (!vis[v]) dfs2(v, id);
    };
    while (!order.empty()) {
        int u = order.top(); order.pop();
        if (!vis[u]) {
            dfs2(u, scc_cnt);
            scc_cnt++;
        }
    }
    vector<int> scc_size(scc_cnt, 0);
    for (int i = 1; i <= n; i++) scc_size[scc[i]]++;
    vector<set<int>> dag_set(scc_cnt);
    for (int u = 1; u <= n; u++) {
        int s1 = scc[u];
        for (int v : adj[u]) {
            int s2 = scc[v];
            if (s1 != s2) {
                dag_set[s1].insert(s2);
            }
        }
    }
    vector<vector<int>> dag(scc_cnt);
    vector<int> dag_indeg(scc_cnt, 0);
    for (int i = 0; i < scc_cnt; i++) {
        for (int j : dag_set[i]) {
            dag[i].push_back(j);
            dag_indeg[j]++;
        }
    }
    queue<int> q;
    vector<int> temp_indeg = dag_indeg;
    vector<int> topo;
    for (int i = 0; i < scc_cnt; i++) if (temp_indeg[i] == 0) q.push(i);
    while (!q.empty()) {
        int i = q.front(); q.pop();
        topo.push_back(i);
        for (int j : dag[i]) {
            temp_indeg[j]--;
            if (temp_indeg[j] == 0) q.push(j);
        }
    }
    vector<long long> reach_size(scc_cnt, 0);
    for (int idx = topo.size() - 1; idx >= 0; idx--) {
        int i = topo[idx];
        reach_size[i] = scc_size[i];
        for (int j : dag[i]) {
            reach_size[i] += reach_size[j];
        }
    }
    vector<int> candidates;
    for (int i = 1; i <= n; i++) {
        if (reach_size[scc[i]] == n) {
            candidates.push_back(i);
        }
    }
    sort(candidates.begin(), candidates.end(), [&](int x, int y) {
        if (outdeg[x] != outdeg[y]) return outdeg[x] < outdeg[y];
        return x < y;
    });
    vector<char> visited(n + 1, 0);
    vector<int> path;
    function<bool(int, int)> dfs = [&](int u, int count) -> bool {
        path.push_back(u);
        visited[u] = 1;
        bool res = (count == n);
        if (!res) {
            for (int v : adj[u]) {
                if (visited[v] == 0) {
                    if (dfs(v, count + 1)) {
                        res = true;
                        break;
                    }
                }
            }
        }
        if (!res) {
            path.pop_back();
            visited[u] = 0;
        }
        return res;
    };
    vector<int> the_path;
    bool found_ham = false;
    for (int start : candidates) {
        fill(visited.begin(), visited.end(), 0);
        path.clear();
        if (dfs(start, 1)) {
            the_path = path;
            found_ham = true;
            break;
        }
    }
    if (found_ham && the_path.size() == static_cast<size_t>(n)) {
        cout << n << '\n';
        for (size_t i = 0; i < the_path.size(); i++) {
            cout << the_path[i];
            if (i + 1 < the_path.size()) cout << " ";
            else cout << '\n';
        }
    } else {
        int some = 1;
        if (!candidates.empty()) some = candidates[0];
        cout << 1 << '\n' << some << '\n';
    }
    return 0;
}