#include <bits/stdc++.h>
using namespace std;

int n;
vector<vector<int>> adj;
vector<int> in_deg;

bool ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    char c;
    cin >> c;
    return c == '<';
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    adj.resize(n + 1);
    in_deg.assign(n + 1, 0);

    for (int i = 1; i < n; ++i) {
        if (ask(i, i + 1)) {
            adj[i].push_back(i + 1);
            ++in_deg[i + 1];
        } else {
            adj[i + 1].push_back(i);
            ++in_deg[i];
        }
    }

    for (int i = 1; i <= n - 2; i += 2) {
        if (ask(i, i + 2)) {
            adj[i].push_back(i + 2);
            ++in_deg[i + 2];
        } else {
            adj[i + 2].push_back(i);
            ++in_deg[i];
        }
    }

    vector<int> order;
    priority_queue<int, vector<int>, greater<int>> pq;
    for (int i = 1; i <= n; ++i) {
        if (in_deg[i] == 0) pq.push(i);
    }

    while (!pq.empty()) {
        int u = pq.top();
        pq.pop();
        order.push_back(u);
        for (int v : adj[u]) {
            if (--in_deg[v] == 0) pq.push(v);
        }
    }

    vector<int> ans(n + 1);
    int val = 1;
    for (int idx : order) ans[idx] = val++;

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << ans[i];
    cout << endl;

    return 0;
}