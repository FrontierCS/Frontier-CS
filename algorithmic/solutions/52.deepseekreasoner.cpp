#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;
int query_cache[MAXN][MAXN];

int n, l1, l2;
int query_count = 0;

int ask(int l, int r) {
    if (query_cache[l][r] != -1) return query_cache[l][r];
    cout << "1 " << l << " " << r << endl;
    cout.flush();
    int res;
    cin >> res;
    query_cache[l][r] = res;
    query_count++;
    // In case we exceed limit, but we trust it won't happen.
    return res;
}

vector<int> get_left_neighbors(int i) {
    vector<int> res;
    if (i <= 1) return res;
    int g1 = ask(1, i) - ask(1, i-1);
    if (g1 == 1) {
        // no neighbor
        return res;
    } else if (g1 == 0) {
        // one neighbor
        int lo = 1, hi = i-1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int g_mid = ask(mid, i) - ask(mid, i-1);
            if (g_mid == 1) hi = mid;
            else lo = mid + 1;
        }
        // neighbor at lo-1
        res.push_back(lo - 1);
    } else { // g1 == -1
        // two neighbors
        // find first l where g(l) >= 0
        int lo = 1, hi = i-1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int g_mid = ask(mid, i) - ask(mid, i-1);
            if (g_mid >= 0) hi = mid;
            else lo = mid + 1;
        }
        int j1 = lo - 1;
        res.push_back(j1);
        // find first l where g(l) == 1 (starting from j1+1)
        lo = j1 + 1, hi = i-1;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int g_mid = ask(mid, i) - ask(mid, i-1);
            if (g_mid == 1) hi = mid;
            else lo = mid + 1;
        }
        int j2 = lo - 1;
        res.push_back(j2);
    }
    return res;
}

vector<int> get_right_neighbors(int i) {
    vector<int> res;
    if (i >= n) return res;
    int h_n = ask(i, n) - ask(i+1, n);
    if (h_n == 1) {
        // no neighbor
        return res;
    } else if (h_n == 0) {
        // one neighbor
        int lo = i+1, hi = n;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int h_mid = ask(i, mid) - ask(i+1, mid);
            if (h_mid == 0) hi = mid;
            else lo = mid + 1;
        }
        // neighbor at lo
        res.push_back(lo);
    } else { // h_n == -1
        // two neighbors
        // find smallest r such that h(r) <= 0
        int lo = i+1, hi = n;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int h_mid = ask(i, mid) - ask(i+1, mid);
            if (h_mid <= 0) hi = mid;
            else lo = mid + 1;
        }
        int j1 = lo;
        res.push_back(j1);
        // find smallest r such that h(r) == -1
        lo = j1, hi = n;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            int h_mid = ask(i, mid) - ask(i+1, mid);
            if (h_mid == -1) hi = mid;
            else lo = mid + 1;
        }
        int j2 = lo;
        res.push_back(j2);
    }
    return res;
}

int main() {
    cin >> n >> l1 >> l2;
    memset(query_cache, -1, sizeof(query_cache));
    vector<int> adj[n+1];
    
    // Build adjacency graph by finding neighbors for each position
    for (int i = 1; i <= n; i++) {
        vector<int> left_nbrs = get_left_neighbors(i);
        vector<int> right_nbrs = get_right_neighbors(i);
        for (int v : left_nbrs) {
            adj[i].push_back(v);
            adj[v].push_back(i);
        }
        for (int v : right_nbrs) {
            adj[i].push_back(v);
            adj[v].push_back(i);
        }
    }
    
    // Remove duplicate neighbors (just in case)
    for (int i = 1; i <= n; i++) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }
    
    // Find an endpoint (degree 1)
    int start = 1;
    for (int i = 1; i <= n; i++) {
        if (adj[i].size() == 1) {
            start = i;
            break;
        }
    }
    
    // Traverse the path to assign values
    vector<int> ans(n+1);
    int cur = start, prev = -1, val = 1;
    while (true) {
        ans[cur] = val++;
        int nxt = -1;
        for (int v : adj[cur]) {
            if (v != prev) {
                nxt = v;
                break;
            }
        }
        if (nxt == -1) break;
        prev = cur;
        cur = nxt;
    }
    
    // Output the answer
    cout << "3";
    for (int i = 1; i <= n; i++) {
        cout << " " << ans[i];
    }
    cout << endl;
    cout.flush();
    
    return 0;
}