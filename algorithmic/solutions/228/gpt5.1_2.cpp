#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s;
    if (!(cin >> s)) return 0;
    int n = (int)s.size();
    vector<unsigned char> a(n);
    long long onesTotal = 0, zerosTotal = 0;
    for (int i = 0; i < n; ++i) {
        if (s[i] == '1') {
            a[i] = 1;
            ++onesTotal;
        } else {
            a[i] = 0;
            ++zerosTotal;
        }
    }

    if (zerosTotal == 0) {
        cout << 0 << '\n';
        return 0;
    }

    long long D1 = (long long)std::sqrt((long double)zerosTotal);
    long long D2 = (long long)((std::sqrt((long double)4.0L * n + 1.0L) - 1.0L) / 2.0L);
    long long D3 = min(D1, min(D2, onesTotal));
    if (D3 <= 0) {
        cout << 0 << '\n';
        return 0;
    }

    long long ans = 0;

    for (long long d = 1; d <= D3; ++d) {
        long long kll = d * (d + 1);
        if (kll > n) break;
        int k = (int)kll;

        long long ones = 0;
        for (int i = 0; i < k; ++i) ones += a[i];
        if (ones == d) ++ans;

        for (int l = 1, r = k; r < n; ++l, ++r) {
            ones += (int)a[r] - (int)a[l - 1];
            if (ones == d) ++ans;
        }
    }

    cout << ans << '\n';
    return 0;
}