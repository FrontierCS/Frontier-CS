#include <bits/stdc++.h>
using namespace std;
using ll = long long;

ll F(ll m, int T, const vector<int>& pref) {
    if (m <= 0) return 0;
    ll full = m / T;
    int rem = m % T;
    return full * pref[T] + pref[rem];
}

int main() {
    ll n, x, y;
    cin >> n >> x >> y;
    ll g = gcd(x, y);
    ll a = x / g, b = y / g;
    int T = a + b;  // period length
    vector<char> f(T + 1, 0);   // f[i] for i=1..T
    vector<int> pref(T + 1, 0); // prefix sums of f
    for (int i = 1; i <= T; ++i) {
        bool v1 = (i > a) ? f[i - a] : 0;
        bool v2 = (i > b) ? f[i - b] : 0;
        f[i] = !(v1 || v2);
        pref[i] = pref[i - 1] + f[i];
    }
    ll q = n / g;
    ll r = n % g;
    ll ans;
    if (q == 0) {
        ans = n; // each of the n residues has exactly one number
    } else {
        ll Fq = F(q, T, pref);
        ll Fq1 = F(q + 1, T, pref);
        ans = Fq * (g - r) + Fq1 * r;
    }
    cout <<