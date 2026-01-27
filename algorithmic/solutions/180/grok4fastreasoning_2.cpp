#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<vector<int>> adj1(n + 1), adj2(n + 1);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
    }
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }
    vector<vector<int>> sig1(n + 1), sig2(n + 1);
    for (int u = 1; u <= n; u++) {
        vector<int> nd;
        for (int v : adj1[u]) {
            nd.push_back((int)adj1[v].size());
        }
        sort(nd.rbegin(), nd.rend());
        sig1[u] = nd;
    }
    for (int u = 1; u <= n; u++) {
        vector<int> nd;
        for (int v : adj2[u]) {
            nd.push_back((int)adj2[v].size());
        }
        sort(nd.rbegin(), nd.rend());
        sig2[u] = nd;
    }
    auto cmp1 = [&](int a, int b) {
        int da = (int)adj1[a].size();
        int db = (int)adj1[b].size();
        if (da != db) return da > db;
        return sig1[a] > sig1[b];
    };
    auto cmp2 = [&](int a, int b) {
        int da = (int)adj2[a].size();
        int db = (int)adj2[b].size();
        if (da != db) return da > db;
        return sig2[a] > sig2[b];
    };
    vector<int> order1(n);
    iota(order1.begin(), order1.end(), 1);
    sort(order1.begin(), order1.end(), cmp1);
    vector<int> order2(n);
    iota(order2.begin(), order2.end(), 1);
    sort(order2.begin(), order2.end(), cmp2);
    vector<int> perm(n + 1);
    for (int i = 0; i < n; i++) {
        perm[order2[i]] = order1[i];
    }
    for (int i = 1; i <= n; i++) {
        cout << perm[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}