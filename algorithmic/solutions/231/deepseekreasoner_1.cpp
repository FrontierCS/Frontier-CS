#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n, m, T;
    cin >> n >> m >> T;

    vector<vector<int>> adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
        adj[a].push_back(b);
    }

    // Compute topological order
    vector<int> indeg(n + 1, 0);
    for (int u = 1; u <= n; ++u)
        for (int v : adj[u])
            indeg[v]++;

    queue<int> q;
    for (int u = 1; u <= n; ++u)
        if (indeg[u] == 0)
            q.push(u);

    vector<int> topo;
    while (!q.empty()) {
        int u = q.front();
        q.pop();
        topo.push_back(u);
        for (int v : adj[u]) {
            indeg[v]--;
            if (indeg[v] == 0)
                q.push(v);
        }
    }

    // Compute Grundy numbers in reverse topological order
    vector<int> grundy(n + 1, 0);
    reverse(topo.begin(), topo.end());
    for (int u : topo) {
        vector<bool> seen(n + 1, false);
        for (int v : adj[u])
            seen[grundy[v]] = true;
        int g = 0;
        while (seen[g])
            g++;
        grundy[u] = g;
    }

    // No edge modifications
    cout << 0 << endl;
    cout.flush();

    // Process T rounds
    for (int round = 0; round < T; ++round) {
        int found = -1;
        for (int i = 1; i <= n; ++i) {
            cout << "? 1 " << i << endl;
            cout.flush();
            string res;
            cin >> res;
            if (res == "Lose") {
                found = i;
                break;
            }
        }
        if (found == -1)
            found = 1; // should never happen
        cout << "! " << found << endl;
        cout.flush();
        string verdict;
        cin >> verdict;
        if (verdict == "Wrong")
            break;
    }
    return 0;
}