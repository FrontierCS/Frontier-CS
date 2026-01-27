#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<vector<int>> a(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            int x; 
            cin >> x;
            a[i][j] = x;
            a[j][i] = x;
        }
    }

    int zero_idx = -1;
    for (int i = 1; i <= n; ++i) {
        vector<char> seen(n, 0);
        int cnt = 0;
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            int v = a[i][j];
            if (0 <= v && v < n && !seen[v]) {
                seen[v] = 1;
                cnt++;
            }
        }
        if (cnt == n - 1) {
            zero_idx = i;
            break;
        }
    }

    vector<int> ans(n + 1, 0);
    ans[zero_idx] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == zero_idx) continue;
        ans[i] = a[zero_idx][i];
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}