#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m, T;
    cin >> n >> m >> T;

    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int a, b;
        cin >> a >> b;
        adj[a].push_back(b);
        indeg[b]++;
    }

    // Topological sort
    vector<int> topo;
    queue<int> q;
    for (int i = 1; i <= n; i++) {
        if (indeg[i] == 0) q.push(i);
    }
    while (!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for (int v : adj[u]) {
            indeg[v]--;
            if (indeg[v] == 0) q.push(v);
        }
    }

    // Compute Grundy numbers
    vector<int> grundy(n + 1, 0);
    vector<bool> mex_arr(n + 2, false); // temporary array for mex calculation
    for (int i = n - 1; i >= 0; i--) {
        int u = topo[i];
        for (int v : adj[u]) {
            mex_arr[grundy[v]] = true;
        }
        int g = 0;
        while (mex_arr[g]) g++;
        grundy[u] = g;
        // reset mex_arr
        for (int v : adj[u]) {
            mex_arr[grundy[v]] = false;
        }
    }

    // Phase 1: Graph modification (none)
    cout << 0 << endl;
    cout.flush();

    // Phase 2: T rounds
    for (int round = 0; round < T; round++) {
        int guess = 1;
        for (int u = 1; u <= n; u++) {
            cout << "? 1 " << u << endl;
            cout.flush();
            string ans;
            cin >> ans;
            if (ans == "Lose") {
                guess = u;
                break;
            }
        }
        cout << "! " << guess << endl;
        cout.flush();
        string res;
        cin >> res;
        if (res == "Wrong") {
            return 0;
        }
    }

    return 0;
}