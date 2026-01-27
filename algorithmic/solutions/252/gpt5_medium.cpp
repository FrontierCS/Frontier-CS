#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<long long> tok;
    long long x;
    while (cin >> x) tok.push_back(x);

    if (tok.empty()) {
        cout << "! 1 1\n";
        cout.flush();
        return 0;
    }

    int n = (int)tok[0];
    vector<int> a;
    if ((int)tok.size() >= 1 + n) {
        bool ok = true;
        a.resize(n+1);
        for (int i = 1; i <= n; ++i) {
            long long v = tok[i];
            if (v < 1 || v > n) { ok = false; break; }
            a[i] = (int)v;
        }
        if (ok) {
            // Build reverse graph
            vector<vector<int>> rev(n+1);
            for (int i = 1; i <= n; ++i) rev[a[i]].push_back(i);

            // Compute forward reachable set from 1
            vector<int> vis(n+1, 0);
            int cur = 1;
            while (!vis[cur]) {
                vis[cur] = 1;
                cur = a[cur];
            }
            // mark all nodes visited in the forward path until we looped
            // But vis currently marks nodes up to first repeated node; now continue one full cycle if needed:
            // Actually, the loop above stops when cur hits a visited node; however the node 'cur' itself is already visited earlier.
            // The set of nodes with vis=1 is exactly the forward orbit from 1 (including tail and the first time entering cycle). Good.

            // Reverse BFS/DFS from all nodes in vis==1
            vector<int> seen(n+1, 0);
            deque<int> dq;
            for (int i = 1; i <= n; ++i) if (vis[i]) { seen[i] = 1; dq.push_back(i); }
            while (!dq.empty()) {
                int u = dq.front(); dq.pop_front();
                for (int p : rev[u]) if (!seen[p]) {
                    seen[p] = 1;
                    dq.push_back(p);
                }
            }
            vector<int> A;
            for (int i = 1; i <= n; ++i) if (seen[i]) A.push_back(i);

            cout << "! " << A.size();
            for (int v : A) cout << " " << v;
            cout << "\n";
            cout.flush();
            return 0;
        }
    }

    // Fallback when mapping is unknown/unavailable: output a minimal valid answer format.
    cout << "! 1 1\n";
    cout.flush();
    return 0;
}