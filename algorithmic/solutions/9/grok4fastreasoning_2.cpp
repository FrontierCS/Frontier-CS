#include <bits/stdc++.h>
using namespace std;

void compute_dist(int src, int n, vector<int>& d, const vector<vector<pair<int, int>>>& adj) {
    d.assign(n + 1, -1);
    d[src] = 0;
    queue<int> q;
    q.push(src);
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        for (auto [v, _] : adj[u]) {
            if (d[v] == -1) {
                d[v] = d[u] + 1;
                q.push(v);
            }
        }
    }
}

void dfs(int u, int par, const vector<vector<long long>>& wt, vector<long long>& A, vector<long long>& B, vector<int>& best_matched_to, const vector<vector<pair<int, int>>>& adj) {
    vector<int> childs;
    long long sum_max = 0;
    for (auto [v, _] : adj[u]) {
        if (v == par) continue;
        dfs(v, u, wt, A, B, best_matched_to, adj);
        childs.push_back(v);
        long long mxv = max(A[v], B[v]);
        sum_max += mxv;
    }
    A[u] = sum_max;
    B[u] = LLONG_MIN / 2;
    best_matched_to[u] = -1;
    int nc = childs.size();
    if (nc == 0) return;
    for (int v : childs) {
        long long mxv = max(A[v], B[v]);
        long long other_sum = sum_max - mxv;
        long long wtv = wt[u][v];
        if (wtv <= LLONG_MIN / 4) continue;
        long long val = wtv + A[v] + other_sum;
        if (val > B[u]) {
            B[u] = val;
            best_matched_to[u] = v;
        }
    }
}

void extract(int u, int par, bool already_matched, vector<int>& selected, const vector<long long>& A, const vector<long long>& B, const vector<int>& best_matched_to, const vector<vector<pair<int, int>>>& adj) {
    if (already_matched) {
        for (auto [v, eid] : adj[u]) {
            if (v == par) continue;
            bool child_use_b = (B[v] >= A[v] && B[v] != LLONG_MIN / 2);
            extract(v, u, child_use_b, selected, A, B, best_matched_to, adj);
        }
        return;
    }
    bool use_b = false;
    if (B[u] > A[u]) use_b = true;
    else if (B[u] == A[u] && best_matched_to[u] != -1) use_b = true;
    if (!use_b) {
        for (auto [v, eid] : adj[u]) {
            if (v == par) continue;
            bool child_use_b = (B[v] >= A[v] && B[v] != LLONG_MIN / 2);
            extract(v, u, child_use_b, selected, A, B, best_matched_to, adj);
        }
        return;
    }
    int w = best_matched_to[u];
    if (w == -1) {
        for (auto [v, eid] : adj[u]) {
            if (v == par) continue;
            bool child_use_b = (B[v] >= A[v] && B[v] != LLONG_MIN / 2);
            extract(v, u, child_use_b, selected, A, B, best_matched_to, adj);
        }
        return;
    }
    int eid_chosen = -1;
    for (auto [vv, ee] : adj[u]) {
        if (vv == w) {
            eid_chosen = ee;
            break;
        }
    }
    if (eid_chosen != -1) {
        selected.push_back(eid_chosen);
    }
    extract(w, u, true, selected, A, B, best_matched_to, adj);
    for (auto [v, eid] : adj[u]) {
        if (v == par || v == w) continue;
        bool child_use_b = (B[v] >= A[v] && B[v] != LLONG_MIN / 2);
        extract(v, u, child_use_b, selected, A, B, best_matched_to, adj);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int n;
        cin >> n;
        vector<int> p(n + 1);
        for (int i = 1; i <= n; i++) {
            cin >> p[i];
        }
        vector<vector<pair<int, int>>> adj(n + 1);
        vector<pair<int, int>> edge_list(n);
        for (int i = 1; i < n; i++) {
            int u, v;
            cin >> u >> v;
            edge_list[i] = {u, v};
            adj[u].emplace_back(v, i);
            adj[v].emplace_back(u, i);
        }
        vector<vector<int>> dist(n + 1, vector<int>(n + 1));
        for (int src = 1; src <= n; src++) {
            vector<int> d(n + 1, -1);
            d[src] = 0;
            queue<int> q;
            q.push(src);
            while (!q.empty()) {
                int u = q.front();
                q.pop();
                for (auto [v, _] : adj[u]) {
                    if (d[v] == -1) {
                        d[v] = d[u] + 1;
                        q.push(v);
                    }
                }
            }
            for (int j = 1; j <= n; j++) {
                dist[src][j] = d[j];
            }
        }
        vector<vector<int>> operations;
        int max_steps = 4 * n;
        int step = 0;
        vector<int> current_p = p;
        p = current_p; // ensure
        while (true) {
            bool issorted = true;
            for (int i = 1; i <= n; i++) {
                if (p[i] != i) {
                    issorted = false;
                    break;
                }
            }
            if (issorted) break;
            if (step >= max_steps) break;
            step++;
            vector<vector<long long>> wt(n + 1, vector<long long>(n + 1, LLONG_MIN / 2));
            for (int eid = 1; eid < n; eid++) {
                int u = edge_list[eid].first;
                int v = edge_list[eid].second;
                int a = p[u];
                int b = p[v];
                long long da_old = dist[u][a];
                long long da_new = dist[v][a];
                long long db_old = dist[v][b];
                long long db_new = dist[u][b];
                long long red = (da_old - da_new) + (db_old - db_new);
                if (red >= 0) {
                    wt[u][v] = red;
                    wt[v][u] = red;
                }
            }
            vector<long long> A(n + 1);
            vector<long long> B(n + 1);
            vector<int> best_matched_to(n + 1, -1);
            dfs(1, 0, wt, A, B, best_matched_to, adj);
            vector<int> selected;
            extract(1, 0, false, selected, A, B, best_matched_to, adj);
            bool still_not_sorted = true;
            for (int i = 1; i <= n; i++) {
                if (p[i] != i) {
                    still_not_sorted = true;
                    break;
                }
                still_not_sorted = false;
            }
            if (selected.empty() && still_not_sorted) {
                long long best_r = -1;
                int best_e = -1;
                for (int e = 1; e < n; e++) {
                    int u = edge_list[e].first;
                    int v = edge_list[e].second;
                    int a = p[u];
                    int b = p[v];
                    long long da_old = dist[u][a];
                    long long da_new = dist[v][a];
                    long long db_old = dist[v][b];
                    long long db_new = dist[u][b];
                    long long r = (da_old - da_new) + (db_old - db_new);
                    if (r >= 0 && r > best_r) {
                        best_r = r;
                        best_e = e;
                    }
                }
                if (best_e != -1) {
                    selected = {best_e};
                }
            }
            if (selected.empty()) {
                break;
            }
            for (int e : selected) {
                int u = edge_list[e].first;
                int v = edge_list[e].second;
                swap(p[u], p[v]);
            }
            operations.push_back(selected);
        }
        cout << operations.size() << '\n';
        for (auto& op : operations) {
            cout << op.size();
            for (int e : op) {
                cout << " " << e;
            }
            cout << '\n';
        }
    }
    return 0;
}