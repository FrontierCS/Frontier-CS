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
    vector<int> deg1(n + 1), deg2(n + 1);
    for (int i = 1; i <= n; i++) {
        deg1[i] = adj1[i].size();
        deg2[i] = adj2[i].size();
    }
    vector<vector<int>> sig1(n + 1), sig2(n + 1);
    for (int i = 1; i <= n; i++) {
        for (int j : adj1[i]) {
            sig1[i].push_back(deg1[j]);
        }
        sort(sig1[i].begin(), sig1[i].end());
        for (int j : adj2[i]) {
            sig2[i].push_back(deg2[j]);
        }
        sort(sig2[i].begin(), sig2[i].end());
    }
    vector<int> order1(n);
    for (int i = 0; i < n; i++) order1[i] = i + 1;
    sort(order1.begin(), order1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        if (sig1[a] != sig1[b]) return sig1[a] > sig1[b];
        return a < b;
    });
    vector<int> order2(n);
    for (int i = 0; i < n; i++) order2[i] = i + 1;
    sort(order2.begin(), order2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        if (sig2[a] != sig2[b]) return sig2[a] > sig2[b];
        return a < b;
    });
    vector<int> p(n + 1);
    for (int k = 0; k < n; k++) {
        int u = order2[k];
        int j = order1[k];
        p[u] = j;
    }
    for (int i = 1; i <= n; i++) {
        cout << p[i];
        if (i < n) cout << " ";
        else cout << "\n";
    }
    return 0;
}