#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n;
    long long l1, l2;
    long long qcnt = 0;

    vector<vector<int>> edgeCache; // -1 unknown, else internal edge count in [l,r]

    int askSegments(int l, int r) {
        cout << "1 " << l << " " << r << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        ++qcnt;
        return x;
    }

    int getE(int l, int r) {
        if (l >= r) return 0;
        int &res = edgeCache[l][r];
        if (res != -1) return res;
        int seg = askSegments(l, r);
        res = (r - l + 1) - seg;
        return res;
    }

    // number of edges from vertex at position i to positions in [t, i-1]
    int leftEdges(int i, int t) {
        if (t > i - 1) return 0;
        return getE(t, i) - getE(t, i - 1);
    }

    // number of edges from vertex at position i to positions in [i+1, r]
    int rightEdges(int i, int r) {
        if (r < i + 1) return 0;
        return getE(i, r) - getE(i + 1, r);
    }

    int findLeftBoundaryLE(int i, int maxVal) {
        int lo = 1, hi = i;
        while (lo < hi) {
            int mid = (lo + hi) >> 1;
            if (leftEdges(i, mid) <= maxVal) hi = mid;
            else lo = mid + 1;
        }
        return lo;
    }

    int findRightBoundaryGE(int i, int target) {
        int lo = i + 1, hi = n;
        while (lo < hi) {
            int mid = (lo + hi) >> 1;
            if (rightEdges(i, mid) >= target) hi = mid;
            else lo = mid + 1;
        }
        return lo;
    }

    void addEdge(int u, int v, vector<vector<int>>& adj, vector<vector<char>>& has) {
        if (u == v) return;
        if (!has[u][v]) {
            has[u][v] = has[v][u] = 1;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    void solve() {
        cin >> n >> l1 >> l2;

        edgeCache.assign(n + 2, vector<int>(n + 2, -1));

        vector<vector<int>> adj(n + 1);
        vector<vector<char>> has(n + 1, vector<char>(n + 1, 0));

        for (int i = 1; i <= n; i++) {
            int leftDeg = 0, rightDeg = 0;

            if (i >= 2) leftDeg = leftEdges(i, 1);
            if (i <= n - 1) rightDeg = rightEdges(i, n);

            if (leftDeg >= 1) {
                int t0 = findLeftBoundaryLE(i, 0); // first t with leftEdges(i,t) == 0
                int j2 = t0 - 1;
                addEdge(i, j2, adj, has);
            }
            if (leftDeg == 2) {
                int t1 = findLeftBoundaryLE(i, 1); // first t with leftEdges(i,t) <= 1
                int j1 = t1 - 1;
                addEdge(i, j1, adj, has);
            }

            if (rightDeg >= 1) {
                int j1 = findRightBoundaryGE(i, 1);
                addEdge(i, j1, adj, has);
            }
            if (rightDeg == 2) {
                int j2 = findRightBoundaryGE(i, 2);
                addEdge(i, j2, adj, has);
            }
        }

        // Traverse the path
        vector<int> deg(n + 1, 0);
        for (int i = 1; i <= n; i++) deg[i] = (int)adj[i].size();

        int start = 1;
        if (n == 1) {
            start = 1;
        } else {
            for (int i = 1; i <= n; i++) {
                if (deg[i] == 1) { start = i; break; }
            }
        }

        vector<int> order;
        order.reserve(n);
        int prev = 0, cur = start;
        for (int step = 0; step < n; step++) {
            order.push_back(cur);
            int nxt = 0;
            for (int v : adj[cur]) if (v != prev) { nxt = v; break; }
            prev = cur;
            cur = nxt;
            if (cur == 0 && step != n - 1) break;
        }

        // If something went wrong, still output a valid permutation
        vector<int> p(n + 1, 0);
        if ((int)order.size() == n) {
            for (int idx = 0; idx < n; idx++) p[order[idx]] = idx + 1;
        } else {
            for (int i = 1; i <= n; i++) p[i] = i;
        }

        cout << "3";
        for (int i = 1; i <= n; i++) cout << " " << p[i];
        cout << "\n";
        cout.flush();
        exit(0);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Solver s;
    s.solve();
    return 0;
}