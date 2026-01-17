#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();

    vector<int> pref(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pref[i + 1] = pref[i] + (s[i] == '1');
    }

    long long ans = 0;
    for (long long k = 1;; ++k) {
        long long L = k * k + k;
        if (L > n) break;
        int len = (int)L;
        for (int i = len; i <= n; ++i) {
            if (pref[i] - pref[i - len] == k) {
                ++ans;
            }
        }
    }

    cout << ans << '\n';
    return 0;
}