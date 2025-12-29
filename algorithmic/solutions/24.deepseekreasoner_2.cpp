#include <bits/stdc++.h>
using namespace std;

int n;
vector<string> C;

bool find_ham_path_start(int start, const vector<int>& component,
                         const vector<vector<int>>& adj, vector<int>& path) {
    int comp_size = component.size();
    if (comp_size == 0) return true;
    unordered_set<int> comp_set(component.begin(), component.end());
    if (!comp_set.count(start)) return false;
    vector<bool> visited(n + 1, false);
    for (int v = 1; v <= n; ++v)
        if (!comp_set.count(v)) visited[v] = true;
    path.clear();
    path.push_back(start);
    visited[start] = true;

    function<bool(int, int)> dfs = [&](int u, int cnt) -> bool {
        if (cnt == comp_size) return true;
        for (int v : adj[u]) {
            if (comp_set.count(v) && !visited[v]) {
                visited[v] = true;
                path.push_back(v);
                if (dfs(v, cnt + 1)) return true;
                path.pop_back();
                visited[v] = false;
            }
        }
        return false;
    };
    return dfs(start, 1);
}

bool find_ham_path_any(const vector<int>& component,
                       const vector<vector<int>>& adj, vector<int>& path) {
    if (component.empty()) return true;
    vector<int> starts = component;
    sort(starts.begin(), starts.end());
    int tries = min((int)starts.size(), 5);
    for (int i = 0; i < tries; ++i) {
        int start = starts[i];
        if (find_ham_path_start(start, component, adj, path)) return true;
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    while (cin >> n) {
        C.resize(n + 1);
        for (int i = 1; i <= n; ++i) {
            string s;
            cin >> s;
            C[i] = " " + s;
        }
        vector<vector<int>> candidates;
        for (int k = 0; k <= 1; ++k) {
            vector<vector<int>> adj(n + 1);
            for (int i = 1; i <= n; ++i)
                for (int j = i + 1; j <= n; ++j)
                    if (C[i][j] - '0' == k) {
                        adj[i].push_back(j);
                        adj[j].push_back(i);
                    }
            for (int i = 1; i <= n; ++i)
                sort(adj[i].begin(), adj[i].end());

            vector<bool> vis(n + 1, false);
            vector<vector<int>> comps;
            for (int i = 1; i <= n; ++i) {
                if (!vis[i]) {
                    vector<int> comp;
                    queue<int> q;
                    q.push(i);
                    vis[i] = true;
                    while (!q.empty()) {
                        int u = q.front();
                        q.pop();
                        comp.push_back(u);
                        for (int v : adj[u])
                            if (!vis[v]) {
                                vis[v] = true;
                                q.push(v);
                            }
                    }
                    comps.push_back(comp);
                }
            }
            if (comps.size() == 1) {
                vector<int> path;
                if (find_ham_path_any(comps[0], adj, path))
                    candidates.push_back(path);
            } else if (comps.size() == 2) {
                vector<int> compA = comps[0], compB = comps[1];
                if (compA.size() > compB.size()) swap(compA, compB);
                if (compA.size() == 1) {
                    int v = compA[0];
                    bool has_edge = false;
                    for (int u : compB)
                        if (C[v][u] - '0' == 1 - k) {
                            has_edge = true;
                            break;
                        }
                    if (!has_edge) continue;

                    vector<int> pathB;
                    if (find_ham_path_any(compB, adj, pathB)) {
                        if (C[v][pathB[0]] - '0' == 1 - k) {
                            vector<int> cand = {v};
                            cand.insert(cand.end(), pathB.begin(), pathB.end());
                            candidates.push_back(cand);
                        }
                        if (C[pathB.back()][v] - '0' == 1 - k) {
                            vector<int> cand = pathB;
                            cand.push_back(v);
                            candidates.push_back(cand);
                        }
                    }

                    vector<int> neighbors;
                    for (int u : compB)
                        if (C[v][u] - '0' == 1 - k) neighbors.push_back(u);
                    sort(neighbors.begin(), neighbors.end());
                    int tries_nb = min((int)neighbors.size(), 5);
                    for (int idx = 0; idx < tries_nb; ++idx) {
                        int u = neighbors[idx];
                        vector<int> path_start_u;
                        if (find_ham_path_start(u, compB, adj, path_start_u)) {
                            vector<int> cand1 = {v};
                            cand1.insert(cand1.end(), path_start_u.begin(),
                                         path_start_u.end());
                            candidates.push_back(cand1);
                            vector<int> rev = path_start_u;
                            reverse(rev.begin(), rev.end());
                            vector<int> cand2 = rev;
                            cand2.push_back(v);
                            candidates.push_back(cand2);
                        }
                    }
                }
            }
        }
        if (candidates.empty()) {
            cout << -1 << "\n";
        } else {
            vector<int> best = candidates[0];
            for (const auto& cand : candidates)
                if (cand < best) best = cand;
            for (int i = 0; i < n; ++i)
                cout << best[i] << (i == n - 1 ? '\n' : ' ');
        }
    }
    return 0;
}