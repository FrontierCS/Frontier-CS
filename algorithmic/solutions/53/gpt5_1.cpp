#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        vector<int> ans(n);
        for (int i = 0; i < n; ++i) {
            ans[i] = (i + 1) % n + 1;
        }
        for (int i = 0; i < n; ++i) {
            cout << ans[i] << (i + 1 == n ? '\n' : ' ');
        }
    }
    return 0;
}