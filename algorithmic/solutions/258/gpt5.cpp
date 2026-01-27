#include <bits/stdc++.h>
using namespace std;

pair<int,int> query(const vector<int>& vec) {
    cout << "? " << vec.size();
    for (int x : vec) cout << " " << x;
    cout << endl;
    cout.flush();
    int x, d;
    if (!(cin >> x >> d)) {
        exit(0);
    }
    if (x == -1 && d == -1) exit(0);
    return {x, d};
}

void answer(int a, int b) {
    cout << "! " << a << " " << b << endl;
    cout.flush();
    string res;
    if (!(cin >> res)) exit(0);
    if (res != "Correct") exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n+1);
        for (int i = 0; i < n-1; ++i) {
            int u,v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        // Initial query: all nodes
        vector<int> all(n);
        iota(all.begin(), all.end(), 1);
        auto first = query(all);
        int r = first.first;
        int D = first.second;

        // BFS from r
        vector<int> dist(n+1, -1);
        queue<int> q;
        dist[r] = 0;
        q.push(r);
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (dist[v] == -1) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }

        int maxDepth = 0;
        for (int i = 1; i <= n; ++i) maxDepth = max(maxDepth, dist[i]);

        vector<vector<int>> levels(maxDepth+1);
        for (int i = 1; i <= n; ++i) {
            levels[dist[i]].push_back(i);
        }

        // Binary search for farthest distance from r along the hidden path
        int lo = 0, hi = maxDepth;
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            auto ans = query(levels[mid]);
            if (ans.second == D) lo = mid;
            else hi = mid - 1;
        }

        // Get one endpoint at distance lo from r
        auto ep = query(levels[lo]);
        int s = ep.first;

        // BFS from s to get the other endpoint at distance D
        vector<int> distS(n+1, -1);
        queue<int> qs;
        distS[s] = 0;
        qs.push(s);
        while (!qs.empty()) {
            int u = qs.front(); qs.pop();
            for (int v : adj[u]) {
                if (distS[v] == -1) {
                    distS[v] = distS[u] + 1;
                    qs.push(v);
                }
            }
        }

        vector<int> cand;
        for (int i = 1; i <= n; ++i) if (distS[i] == D) cand.push_back(i);
        auto other = query(cand);
        int f = other.first;

        answer(s, f);
    }
    return 0;
}