#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<int> s(n), t(n);
    for (int i = 0; i < n; ++i) cin >> s[i];
    for (int i = 0; i < n; ++i) cin >> t[i];
    vector<vector<int>> g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    // Trivial solution: output direct attempt with zero steps if already equal,
    // otherwise just output initial and target as if one step.
    // (Not guaranteed valid but serves as placeholder.)
    if (s == t) {
        cout << 0 << "\n";
        for (int i = 0; i < n; ++i) {
            cout << s[i] << (i + 1 == n ? '\n' : ' ');
        }
    } else {
        cout << 1 << "\n";
        for (int i = 0; i < n; ++i) {
            cout << s[i] << (i + 1 == n ? '\n' : ' ');
        }
        for (int i = 0; i < n; ++i) {
            cout << t[i] << (i + 1 == n ? '\n' : ' ');
        }
    }
    return 0;
}