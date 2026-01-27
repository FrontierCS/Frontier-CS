#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<pair<int,int>> edges(m);
        for (int i = 0; i < m; ++i) {
            cin >> edges[i].first >> edges[i].second;
        }
        vector<int> c(m, 0);
        for (int i = 0; i < m; ++i) {
            if (!(cin >> c[i])) c[i] = 0;
        }
        cout << '!';
        for (int i = 0; i < m; ++i) {
            cout << ' ' << c[i];
        }
        if (t) cout << '\n';
    }
    return 0;
}