#include <bits/stdc++.h>
using namespace std;

void multi_partition(const vector<int>& S, int start_label, int num_parts, vector<int>& assignment, const vector<vector<int>>& adj, int N) {
    if (S.empty()) return;
    int sz = S.size();
    if (num_parts == 1) {
        for (int v : S) {
            assignment[v] = start_label;
        }
        return;
    }
    // Bisection
    vector<char> inS(N + 1, 0);
    for (int v : S) inS[v] = 1;
    // Get candidate seeds: top degrees
    vector<pair<int, int>> cand;
    for (int v : S) {
        int d = adj[v].size();
        cand.emplace_back(-d, v);
    }
    sort(cand.begin(), cand.end());
    int num_trials_local = (sz > 200 ? 5 : 1);
    int nt = min(num_trials_local, (int)cand.size());
    int best_cut = INT_MAX / 2;
    vector<int> best_left, best_right;
    bool has_valid = false;
    for (int t = 0; t < nt; ++t) {
        int seed = cand[t].second;
        // BFS to get order
        vector<int> order;
        order.reserve(sz);
        vector<char> visited(N + 1, 0);
        queue<int> q;
        // First, BFS from seed
        if (inS[seed] && !visited[seed]) {
            q.push(seed);
            visited[seed] = 1;
            order.push_back(seed);
            while (!q.empty()) {
                int v = q.front(); q.pop();
                for (int w : adj[v]) {
                    if (inS[w] && !visited[w]) {
                        visited[w] = 1;
                        q.push(w);
                        order.push_back(w);
                    }
                }
            }
        }
        // Then, remaining components in S order
        for (int v : S) {
            if (!visited[v]) {
                q.push(v);
                visited[v] = 1;
                order.push_back(v);
                while (!q.empty()) {
                    int u = q.front(); q.pop();
                    for (int w : adj[u]) {
                        if (inS[w] && !visited[w]) {
                            visited[w] = 1;
                            q.push(w);
                            order.push_back(w);
                        }
                    }
                }
            }
        }
        if ((int)order.size() != sz) continue;
        // Split
        int h = sz / 2;
        vector<int> left(order.begin(), order.begin() + h);
        vector<int> right(order.begin() + h, order.end());
        // Compute cut
        vector<char> in_left(N + 1, 0);
        for (int v : left) in_left[v] = 1;
        int cut = 0;
        for (int v : left) {
            for (int w : adj[v]) {
                if (inS[w] && !in_left[w]) ++cut;
            }
        }
        cut /= 2;
        if (cut < best_cut) {
            best_cut = cut;
            best_left = std::move(left);
            best_right = std::move(right);
            has_valid = true;
        }
    }
    // Fallback if no valid
    if (!has_valid) {
        int h = sz / 2;
        best_left.assign(S.begin(), S.begin() + h);
        best_right.assign(S.begin() + h, S.end());
    }
    // Recurse
    multi_partition(best_left, start_label, num_parts / 2, assignment, adj, N);
    multi_partition(best_right, start_label + num_parts / 2, num_parts / 2, assignment, adj, N);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m, k;
    double eps;
    cin >> n >> m >> k >> eps;
    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    for (int i = 1; i <= n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        auto it = unique(adj[i].begin(), adj[i].end());
        adj[i].resize(it - adj[i].begin());
    }
    vector<int> initial_S(n);
    iota(initial_S.begin(), initial_S.end(), 1);
    vector<int> assignment(n + 1, 0);
    multi_partition(initial_S, 1, k, assignment, adj, n);
    for (int i = 1; i <= n; ++i) {
        cout << assignment[i];
        if (i < n) cout << ' ';
        else cout << '\n';
    }
    return 0;
}