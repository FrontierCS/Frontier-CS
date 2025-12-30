#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5010;
const int LOG = 13;

vector<int> adj[MAXN];
int anc[MAXN][LOG];
int depthh[MAXN];
int parentt[MAXN];
int in_time[MAXN], out_time[MAXN];
int timerr;

void dfs_timer(int u, int p) {
    in_time[u] = timerr++;
    for (int v : adj[u]) {
        if (v != p) {
            dfs_timer(v, u);
        }
    }
    out_time[u] = timerr;
}

int get_ancestor(int node, int k) {
    for (int i = 0; i < LOG; i++) {
        if (k & (1 << i)) {
            node = anc[node][i];
        }
    }
    return node;
}

bool is_in_subtree(int y, int x) {
    return (in_time[x] <= in_time[y] && in_time[y] < out_time[x]);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        for (int i = 1; i <= n; i++) adj[i].clear();
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        // BFS for depth and parent
        vector<bool> vis(n + 1, false);
        queue<int> q;
        q.push(1);
        vis[1] = true;
        parentt[1] = 1;
        depthh[1] = 0;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (!vis[v]) {
                    vis[v] = true;
                    parentt[v] = u;
                    depthh[v] = depthh[u] + 1;
                    q.push(v);
                }
            }
        }
        // Binary lifting
        memset(anc, 0, sizeof(anc));
        for (int u = 1; u <= n; u++) {
            anc[u][0] = parentt[u];
        }
        for (int k = 1; k < LOG; k++) {
            for (int u = 1; u <= n; u++) {
                int mid = anc[u][k - 1];
                anc[u][k] = anc[mid][k - 1];
            }
        }
        // Timers
        timerr = 0;
        dfs_timer(1, 0);
        // Possible
        vector<int> possible;
        for (int i = 1; i <= n; i++) possible.push_back(i);
        int cur_m = 0;
        int query_count = 0;
        while (true) {
            if (possible.size() == 1) {
                int s = possible[0];
                int pos = get_ancestor(s, cur_m);
                cout << "! " << pos << endl;
                cout.flush();
                break;
            }
            if (possible.empty()) {
                cout << "! 1" << endl;
                cout.flush();
                break;
            }
            // Check all same current
            int first_c = get_ancestor(possible[0], cur_m);
            bool all_same = true;
            for (size_t i = 1; i < possible.size(); i++) {
                int c = get_ancestor(possible[i], cur_m);
                if (c != first_c) {
                    all_same = false;
                    break;
                }
            }
            if (all_same) {
                cout << "! " << first_c << endl;
                cout.flush();
                break;
            }
            // Compute ww
            vector<int> ww(n + 1, 0);
            for (int s : possible) {
                int c = get_ancestor(s, cur_m);
                ww[c]++;
            }
            // Compute sub_sum
            vector<int> sub_sum(n + 1, 0);
            function<void(int, int)> compute_sub = [&](int u, int p) {
                sub_sum[u] = ww[u];
                for (int v : adj[u]) {
                    if (v != p) {
                        compute_sub(v, u);
                        sub_sum[u] += sub_sum[v];
                    }
                }
            };
            compute_sub(1, 0);
            int total = possible.size();
            // Find best_x
            int best_x = -1;
            int min_diff = INT_MAX;
            for (int xx = 1; xx <= n; xx++) {
                int ss = sub_sum[xx];
                if (ss == 0 || ss == total) continue;
                int diff = abs(ss - total / 2);
                if (diff < min_diff || (diff == min_diff && depthh[xx] < depthh[best_x])) {
                    min_diff = diff;
                    best_x = xx;
                }
            }
            if (best_x == -1) {
                // Fallback
                for (int xx = 1; xx <= n; xx++) {
                    int ss = sub_sum[xx];
                    if (0 < ss && ss < total) {
                        best_x = xx;
                        break;
                    }
                }
            }
            // Query
            cout << "? " << best_x << endl;
            cout.flush();
            int ans;
            cin >> ans;
            query_count++;
            // Update possible
            vector<int> new_pos;
            for (int s : possible) {
                int c = get_ancestor(s, cur_m);
                bool in_sub = is_in_subtree(c, best_x);
                bool should_keep = (ans == 1) ? in_sub : !in_sub;
                if (should_keep) {
                    new_pos.push_back(s);
                }
            }
            possible = new_pos;
            if (ans == 0) {
                cur_m++;
            }
        }
    }
    return 0;
}