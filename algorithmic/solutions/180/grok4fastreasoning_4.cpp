#include <bits/stdc++.h>

using namespace std;

int main() {
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
    vector<int> v1(n);
    iota(v1.begin(), v1.end(), 1);
    sort(v1.begin(), v1.end(), [&](int a, int b) {
        return deg1[a] > deg1[b] || (deg1[a] == deg1[b] && a < b);
    });
    vector<int> v2(n);
    iota(v2.begin(), v2.end(), 1);
    sort(v2.begin(), v2.end(), [&](int a, int b) {
        return deg2[a] > deg2[b] || (deg2[a] == deg2[b] && a < b);
    });
    vector<int> p(n + 1);
    for (int i = 0; i < n; i++) {
        p[v2[i]] = v1[i];
    }
    for (int i = 1; i <= n; i++) {
        if (i > 1) cout << " ";
        cout << p[i];
    }
    cout << endl;
    return 0;
}