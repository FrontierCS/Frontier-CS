#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
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
        auto last = unique(adj[i].begin(), adj[i].end());
        adj[i].erase(last, adj[i].end());
    }
    vector<int> all_verts(n);
    for (int i = 0; i < n; ++i) all_verts[i] = i + 1;
    vector<int> assignment(n + 1, 0);
    vector<int> timestamp(n + 1, 0);
    int timer = 0;
    function<void(vector<int>, int, int)> rec = [&](vector<int> verts, int low, int high) {
        if (verts.empty()) return;
        int s = verts.size();
        int num_parts = high - low + 1;
        if (num_parts == 1) {
            int label = low + 1;
            for (int v : verts) assignment[v] = label;
            return;
        }
        int parts_per_sub = num_parts / 2;
        int left_high = low + parts_per_sub - 1;
        int right_low = low + parts_per_sub;
        timer++;
        for (int v : verts) timestamp[v] = timer;
        vector<pair<int, int>> candidates;
        for (int v : verts) {
            int d = 0;
            for (int w : adj[v]) {
                if (timestamp[w] == timer) ++d;
            }
            candidates.emplace_back(-d, v);
        }
        sort(candidates.begin(), candidates.end());
        int num_trials = min(5, (int)candidates.size());
        int best_cut = INT_MAX;
        vector<int> best_left, best_right;
        for (int tr = 0; tr < num_trials; ++tr) {
            vector<pair<int, int>> starts = candidates;
            int trial_start_id = tr;
            swap(starts[0], starts[trial_start_id]);
            vector<int> order;
            vector<char> vis(n + 1, 0);
            queue<int> q;
            for (auto& p : starts) {
                int v = p.second;
                if (vis[v]) continue;
                q = queue<int>();
                q.push(v);
                vis[v] = 1;
                order.push_back(v);
                while (!q.empty()) {
                    int u = q.front(); q.pop();
                    for (int nei : adj[u]) {
                        if (timestamp[nei] == timer && !vis[nei]) {
                            vis[nei] = 1;
                            q.push(nei);
                            order.push_back(nei);
                        }
                    }
                }
            }
            int split_pos = s / 2;
            vector<char> side(n + 1, 0);
            for (int i = 0; i < split_pos; ++i) side[order[i]] = 1;
            for (int i = split_pos; i < s; ++i) side[order[i]] = 2;
            int this_cut = 0;
            for (int v : verts) {
                for (int w : adj[v]) {
                    if (w > v && timestamp[w] == timer && side[v] != side[w] && side[v] > 0 && side[w] > 0) {
                        ++this_cut;
                    }
                }
            }
            if (this_cut < best_cut) {
                best_cut = this_cut;
                best_left.assign(order.begin(), order.begin() + split_pos);
                best_right.assign(order.begin() + split_pos, order.end());
            }
        }
        rec(best_left, low, left_high);
        rec(best_right, right_low, high);
    };
    rec(all_verts, 0, k - 1);
    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << " ";
        cout << assignment[i];
    }
    cout << "\n";
}