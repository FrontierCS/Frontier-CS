#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> a(n + 1);

    // Determine a[i] for all i via binary search with membership queries
    for (int i = 1; i <= n; ++i) {
        vector<int> cand(n);
        iota(cand.begin(), cand.end(), 1);

        while (cand.size() > 1) {
            int m = (int)cand.size();
            int half = m / 2;
            vector<int> S(cand.begin(), cand.begin() + half);

            cout << "? " << i << " " << 1 << " " << half;
            for (int x : S) cout << " " << x;
            cout << endl;

            int res;
            if (!(cin >> res)) return 0;

            vector<int> next;
            if (res == 1) {
                next = move(S);
            } else {
                next.assign(cand.begin() + half, cand.end());
            }
            cand.swap(next);
        }

        a[i] = cand[0];
    }

    // Build undirected graph of the functional graph and BFS from node 1
    vector<vector<int>> g(n + 1);
    for (int i = 1; i <= n; ++i) {
        int v = a[i];
        g[i].push_back(v);
        if (i != v) g[v].push_back(i);
    }

    vector<int> vis(n + 1, 0);
    vector<int> A;
    queue<int> q;
    q.push(1);
    vis[1] = 1;

    while (!q.empty()) {
        int u = q.front();
        q.pop();
        A.push_back(u);
        for (int to : g[u]) {
            if (!vis[to]) {
                vis[to] = 1;
                q.push(to);
            }
        }
    }

    sort(A.begin(), A.end());

    cout << "! " << A.size();
    for (int x : A) cout << " " << x;
    cout << endl;

    return 0;
}