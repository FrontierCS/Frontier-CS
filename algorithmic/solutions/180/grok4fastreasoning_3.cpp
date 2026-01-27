#include <bits/stdc++.h>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int n, m;
    cin >> n >> m;
    vector<int> deg1(n + 1, 0), deg2(n + 1, 0);
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        deg1[u]++;
        deg1[v]++;
    }
    for (int i = 0; i < m; i++) {
        int u, v;
        cin >> u >> v;
        deg2[u]++;
        deg2[v]++;
    }
    vector<int> verts1(n);
    iota(verts1.begin(), verts1.end(), 1);
    sort(verts1.begin(), verts1.end(), [&](int a, int b) {
        if (deg1[a] != deg1[b]) return deg1[a] > deg1[b];
        return a < b;
    });
    vector<int> verts2(n);
    iota(verts2.begin(), verts2.end(), 1);
    sort(verts2.begin(), verts2.end(), [&](int a, int b) {
        if (deg2[a] != deg2[b]) return deg2[a] > deg2[b];
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