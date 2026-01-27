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
    vector<int> deg1(n + 1), sumnd1(n + 1);
    vector<int> deg2(n + 1), sumnd2(n + 1);
    for (int i = 1; i <= n; i++) {
        deg1[i] = adj1[i].size();
        deg2[i] = adj2[i].size();
    }
    for (int i = 1; i <= n; i++) {
        for (int j : adj1[i]) {
            sumnd1[i] += deg1[j];
        }
        for (int j : adj2[i]) {
            sumnd2[i] += deg2[j];
        }
    }
    vector<int> verts1(n);
    iota(verts1.begin(), verts1.end(), 1);
    sort(verts1.begin(), verts1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        if (sumnd1[a] != sumnd1[b]) return sumnd1[a] > sumnd1[b];
        return a < b;
    });
    vector<int> verts2(n);
    iota(verts2.begin(), verts2.end(), 1);
    sort(verts2.begin(), verts2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
        if (sumnd2[a] != sumnd2[b]) return sumnd2[a] > sumnd2[b];
        return a < b;
    });
    vector<int> p(n + 1);
    for (int i = 0; i < n; i++) {
        p[verts2[i]] = verts1[i];
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << p[i];
    }
    cout << "\n";
    return 0;
}