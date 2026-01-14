#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();

    vector<int> pref(n + 1);
    for (int i = 0; i < n; ++i) {
        pref[i + 1] = pref[i] + (s[i] == '1');
    }

    long long nn = n;
    long long K = sqrtl((long double)nn);
    while ((K + 1) * (K + 1) + (K + 1) <= nn) ++K;
    while (K > 0 && K * K + K > nn) --K;

    long long ans = 0;

    for (int k = 1; k <= (int)K; ++k) {
        int L = k * k + k;
        if (L > n) break;
        int maxStart = n - L;

        int cnt = pref[L] - pref[0];
        if (cnt == k) ++ans;

        for (int i = 1; i <= maxStart; ++i) {
            cnt -= (s[i - 1] == '1');
            cnt += (s[i + L - 1] == '1');
            if (cnt == k) ++ans;
        }
    }

    cout << ans << '\n';
    return 0;
}