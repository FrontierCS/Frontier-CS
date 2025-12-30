#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

vector<int> adj[MAXN];
int parent[MAXN], depth[MAXN];
int tin[MAXN], tout[MAXN];
int timer = 0;

void dfs(int u, int p) {
    parent[u] = p;
    depth[u] = (p == -1 ? 0 : depth[p] + 1);
    tin[u] = ++timer;
    for (int v : adj[u]) {
        if (v != p) dfs(v, u);
    }
    tout[u] = timer;
}

bool is_ancestor(int u, int v) {
    return tin[u] <= tin[v] && tin[v] <= tout[u];
}

int n;
int bit[MAXN];

void bit_add(int idx, int delta) {
    for (; idx <= n; idx += idx & -idx)
        bit[idx] += delta;
}

int bit_sum(int idx) {
    int res = 0;
    for (; idx > 0; idx -= idx & -idx)
        res += bit[idx];
    return res;
}

int range_sum(int l, int r) {
    return bit_sum(r) - bit_sum(l-1);
}

void solve() {
    cin >> n;
    timer = 0;
    for (int i = 1; i <= n; i++) adj[i].clear();
    for (int i = 0; i < n-1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    dfs(1, -1);
    
    vector<bool> active(n+1, true);
    vector<int> cur(n+1);
    for (int i = 1; i <= n; i++) cur[i] = i;
    
    // initialize BIT
    for (int i = 1; i <= n; i++) bit[i] = 0;
    for (int i = 1; i <= n; i++) {
        bit_add(tin[i], 1);
    }
    int active_count = n;
    
    auto all_same = [&]() -> bool {
        if (active_count == 0) return true;
        int first = -1;
        for (int i = 1; i <= n; i++) {
            if (active[i]) {
                if (first == -1) first = cur[i];
                else if (cur[i] != first) return false;
            }
        }
        return true;
    };
    
    int queries_used = 0;
    while (active_count > 1 && !all_same()) {
        // choose query node x
        int best_x = -1, best_score = INT_MAX, best_depth = INT_MAX;
        for (int x = 1; x <= n; x++) {
            int cnt1 = range_sum(tin[x], tout[x]);
            int cnt0 = active_count - cnt1;
            int score = max(cnt1, cnt0);
            if (score < best_score || (score == best_score && depth[x] < best_depth)) {
                best_score = score;
                best_depth = depth[x];
                best_x = x;
            }
        }
        
        cout << "? " << best_x << endl;
        cout.flush();
        queries_used++;
        int ans;
        cin >> ans;
        
        vector<int> ones, zeros;
        for (int i = 1; i <= n; i++) {
            if (!active[i]) continue;
            if (is_ancestor(best_x, cur[i])) {
                ones.push_back(i);
            } else {
                zeros.push_back(i);
            }
        }
        
        if (ans == 1) {
            for (int i : zeros) {
                active[i] = false;
                bit_add(tin[cur[i]], -1);
                active_count--;
            }
        } else {
            for (int i : ones) {
                active[i] = false;
                bit_add(tin[cur[i]], -1);
                active_count--;
            }
            for (int i : zeros) {
                if (cur[i] != 1) {
                    bit_add(tin[cur[i]], -1);
                    cur[i] = parent[cur[i]];
                    bit_add(tin[cur[i]], 1);
                }
            }
        }
    }
    
    int final_node;
    if (active_count == 1) {
        for (int i = 1; i <= n; i++) {
            if (active[i]) {
                final_node = cur[i];
                break;
            }
        }
    } else {
        for (int i = 1; i <= n; i++) {
            if (active[i]) {
                final_node = cur[i];
                break;
            }
        }
    }
    
    cout << "! " << final_node << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    
    return 0;
}