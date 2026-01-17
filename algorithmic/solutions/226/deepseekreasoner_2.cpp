#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    long long n;
    int x, y;
    cin >> n >> x >> y;
    int d = gcd(x, y);  // C++17 has std::gcd, otherwise use __gcd or implement
    int xp = x / d;
    int yp = y / d;
    int T = xp + yp;
    vector<char> a(T + 1, 0);   // a[i] = 1 if i is selected
    vector<int> pref(T + 1, 0); // prefix sums of a
    for (int i = 1; i <= T; ++i) {
        bool cond1 = (i <= xp) || (a[i - xp] == 0);
        bool cond2 = (i <= yp) || (a[i - yp] == 0);
        a[i] = cond1 && cond2;
        pref[i] = pref[i - 1] + a[i];
    }
    int cnt_period = pref[T];
    long long q = n / d;
    int rem = n % d;
    long long ans = 0;
    for (int r = 0; r < d; ++r) {
        long long m;
        if (r == 0) {
            m = q;
        } else {
            m = q + (r <= rem ? 1 : 0);
        }
        if (m == 0) continue;
        long long full = m / T;
        int remainder = m % T;
        ans += full * cnt_period + pref[remainder];
    }
    cout << ans << '\n';
    return 0;
}