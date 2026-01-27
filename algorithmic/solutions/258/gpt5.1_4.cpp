#include <bits/stdc++.h>
using namespace std;

pair<int,int> query(const vector<int> &nodes) {
    cout << "? " << nodes.size();
    for (int v : nodes) cout << ' ' << v;
    cout << endl;
    cout.flush();

    int x, d;
    if (!(cin >> x >> d)) exit(0);
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

void answer(int u, int v) {
    cout << "! " << u << ' ' << v << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> g(n + 1);
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        // First query: all nodes
        vector<int> all(n);
        for (int i = 0; i < n; ++i) all[i] = i + 1;
        auto [r, D] = query(all);

        // BFS from r to get distances
        vector<int> dist_r(n + 1, -1);
        queue<int> q;
        dist_r[r] = 0;
        q.push(r);
        int M = 0;
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) {
                if (dist_r[to] == -1) {
                    dist_r[to] = dist_r[v] + 1;
                    M = max(M, dist_r[to]);
                    q.push(to);
                }
            }
        }

        // Binary search for maximum depth H of path nodes from r
        int low = 0, high = M;
        while (low < high) {
            int mid = (low + high + 1) / 2;
            vector<int> subset;
            subset.reserve(n);
            for (int i = 1; i <= n; ++i)
                if (dist_r[i] >= mid) subset.push_back(i);
            auto [x, d] = query(subset);
            if (d == D) low = mid;
            else high = mid - 1;
        }
        int H = low;

        // Query nodes at exact distance H from r to get one endpoint a
        vector<int> subset_exact;
        subset_exact.reserve(n);
        for (int i = 1; i <= n; ++i)
            if (dist_r[i] == H) subset_exact.push_back(i);
        auto [a, d_dummy] = query(subset_exact);

        // BFS from a to find nodes at distance D (the other endpoint)
        vector<int> dist_a(n + 1, -1);
        dist_a[a] = 0;
        q.push(a);
        while (!q.empty()) {
            int v = q.front(); q.pop();
            for (int to : g[v]) {
                if (dist_a[to] == -1) {
                    dist_a[to] = dist_a[v] + 1;
                    q.push(to);
                }
            }
        }

        vector<int> subset_D;
        subset_D.reserve(n);
        for (int i = 1; i <= n; ++i)
            if (dist_a[i] == D) subset_D.push_back(i);
        auto [b, d_b] = query(subset_D);

        answer(a, b);

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }
    return 0;
}