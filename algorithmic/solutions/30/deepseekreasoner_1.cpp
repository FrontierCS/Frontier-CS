#include <iostream>
#include <vector>
#include <algorithm>
#include <functional>
using namespace std;

const int MAXN = 5005;

vector<int> adj[MAXN];
int parent[MAXN], depth[MAXN];
int tin[MAXN], tout[MAXN];
int timer;

void dfs(int u, int p) {
    parent[u] = p;
    depth[u] = (p == 0 ? 0 : depth[p] + 1);
    tin[u] = ++timer;
    for (int v : adj[u]) {
        if (v == p) continue;
        dfs(v, u);
    }
    tout[u] = timer;
}

bool is_ancestor(int x, int v) {
    return tin[x] <= tin[v] && tin[v] <= tout[x];
}

void solve() {
    int n;
    cin >> n;
    for (int i = 1; i <= n; i++) adj[i].clear();
    for (int i = 0; i < n-1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    timer = 0;
    dfs(1, 0);
    
    vector<int> candidates(n), cur(n);
    for (int i = 0; i < n; i++) {
        candidates[i] = i+1;
        cur[i] = i+1;
    }
    int total = n;
    int queries = 0;
    const int QUERY_LIMIT = 160;
    
    while (true) {
        if (total == 1) break;
        // check if all current positions are the same
        bool all_same = true;
        int first_cur = cur[0];
        for (int i = 1; i < total; i++) {
            if (cur[i] != first_cur) {
                all_same = false;
                break;
            }
        }
        if (all_same) break;
        
        // compute count of current positions
        vector<int> cur_count(n+1, 0);
        for (int i = 0; i < total; i++) {
            cur_count[cur[i]]++;
        }
        
        // compute subtree sums of cur_count
        vector<int> sub_cnt(n+1, 0);
        function<void(int)> dfs_cnt = [&](int u) {
            sub_cnt[u] = cur_count[u];
            for (int v : adj[u]) {
                if (v == parent[u]) continue;
                dfs_cnt(v);
                sub_cnt[u] += sub_cnt[v];
            }
        };
        dfs_cnt(1);
        
        // choose best node to query
        int best_x = 1;
        int best_max = total;
        int best_depth = depth[1];
        for (int x = 1; x <= n; x++) {
            int cnt_in = sub_cnt[x];
            int cnt_out = total - cnt_in;
            int mx = max(cnt_in, cnt_out);
            if (mx < best_max || (mx == best_max && depth[x] < best_depth)) {
                best_max = mx;
                best_depth = depth[x];
                best_x = x;
            }
        }
        
        // ask query
        cout << "? " << best_x << endl;
        cout.flush();
        queries++;
        int r;
        cin >> r;
        
        // update candidates and current positions
        vector<int> new_candidates, new_cur;
        for (int i = 0; i < total; i++) {
            int s = candidates[i];
            int c = cur[i];
            bool in_sub = is_ancestor(best_x, c);
            if (in_sub == r) {
                new_candidates.push_back(s);
                if (!in_sub && c != 1) {
                    c = parent[c];
                }
                new_cur.push_back(c);
            }
        }
        candidates = move(new_candidates);
        cur = move(new_cur);
        total = candidates.size();
        
        if (queries > QUERY_LIMIT) {
            // should not happen, but for safety
            break;
        }
    }
    
    int answer = cur[0];
    cout << "! " << answer << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    
    return 0;
}