#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;
const int MAX_QUERIES = 160;

vector<int> adj[MAXN];
int parent[MAXN], depth[MAXN], tin[MAXN], tout[MAXN];
int timer;

void dfs(int u, int p) {
    parent[u] = p;
    tin[u] = ++timer;
    for (int v : adj[u]) {
        if (v == p) continue;
        depth[v] = depth[u] + 1;
        dfs(v, u);
    }
    tout[u] = timer;
}

bool in_subtree(int x, int v) {
    return tin[x] <= tin[v] && tin[v] <= tout[x];
}

void solve() {
    int n;
    cin >> n;
    for (int i = 1; i <= n; i++) adj[i].clear();
    for (int i = 0; i < n - 1; i++) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    timer = 0;
    depth[1] = 0;
    dfs(1, 0);

    vector<int> active(n);
    iota(active.begin(), active.end(), 1); // active = {1,2,...,n}
    vector<int> cur(n + 1);
    for (int i = 1; i <= n; i++) cur[i] = i;

    int queries_used = 0;
    while (queries_used < MAX_QUERIES) {
        // Check if all current nodes are the same
        bool all_same = true;
        int first_cur = cur[active[0]];
        for (int idx : active) {
            if (cur[idx] != first_cur) {
                all_same = false;
                break;
            }
        }
        if (all_same) {
            cout << "! " << first_cur << endl;
            return;
        }

        // Build frequency array of tin values of current nodes
        vector<int> freq(n + 2, 0);
        for (int idx : active) {
            int c = cur[idx];
            freq[tin[c]]++;
        }
        vector<int> pref(n + 2, 0);
        for (int i = 1; i <= n; i++) {
            pref[i] = pref[i - 1] + freq[i];
        }

        // Find the best query node
        int best_node = -1, best_m = 1e9, best_depth = 1e9;
        for (int x = 1; x <= n; x++) {
            int cnt_in = pref[tout[x]] - pref[tin[x] - 1];
            int a = cnt_in;
            int b = (int)active.size() - a;
            int m = max(a, b);
            if (m < best_m || (m == best_m && depth[x] < best_depth)) {
                best_m = m;
                best_depth = depth[x];
                best_node = x;
            }
        }

        // Make the