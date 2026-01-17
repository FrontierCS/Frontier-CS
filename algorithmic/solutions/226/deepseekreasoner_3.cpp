#include <bits/stdc++.h>
using namespace std;
using ll = long long;

int main() {
    ll n;
    int x, y;
    cin >> n >> x >> y;
    int d = gcd(x, y);
    int p = x / d;
    int q = y / d;
    int T = p + q;
    vector<char> pat(T);
    for (int i = 0; i < T; ++i) {
        bool ok = true;
        if (i >= p) ok = ok && (pat[i-p] == 0);
        if (i >= q) ok = ok && (pat[i-q] == 0);
        pat[i] = ok ? 1 : 0;
    }
    vector<int> pref(T+1);
    for (int i = 0; i < T; ++i) {
        pref[i+1] = pref[i] + pat[i];
    }
    int cnt1 = pref[T];
    auto f = [&](ll L) -> ll {
        if (L <= 0) return 0;
        ll blocks = L / T;
        int rem = L % T;
        return blocks * cnt1 + pref[rem];
    };
    ll ans = 0;
    for (int r = 0; r < d; ++r) {
        ll Lr = (n - r + d - 1) / d;
        ans += f(Lr);
    }
    cout << ans << endl;
    return 0;
}