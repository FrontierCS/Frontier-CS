#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    if(!(cin >> s)) return 0;
    int n = (int)s.size();
    vector<int> pref(n+1, 0);
    for (int i = 0; i < n; ++i) pref[i+1] = pref[i] + (s[i] == '1');

    long long ans = 0;
    // k = number of ones in substring, zeros = k^2 => length = k(k+1)
    // substrings are non-empty => k >= 1
    for (int k = 1;; ++k) {
        long long L = 1LL * k * (k + 1);
        if (L > n) break;
        int len = (int)L;
        int limit = n - len;
        const int *P = pref.data();
        long long cnt = 0;
        for (int t = 0; t <= limit; ++t) {
            if (P[t + len] - P[t] == k) ++cnt;
        }
        ans += cnt;
    }
    cout << ans << '\n';
    return 0;
}