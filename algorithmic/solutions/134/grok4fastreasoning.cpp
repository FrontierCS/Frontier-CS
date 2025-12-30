#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    ll n;
    cin >> n;
    auto ask = [&](ll x, ll y) -> int {
        cout << x << " " << y << "\n";
        int r;
        cin >> r;
        return r;
    };
    ll loa = 1, hia = n;
    ll mid = 1 + (hia - loa) / 2;
    ll lob = 1, hib = n;
    while (lob < hib) {
        ll mb = lob + (hib - lob) / 2;
        int r = ask(mid, mb);
        if (r == 0) return 0;
        if (r == 2) {
            lob = mb + 1;
        } else {
            hib = mb;
        }
    }
    ll bval = lob;
    int r = ask(mid, bval);
    if (r == 0) return 0;
    ll a_lo = 1, a_hi = n;
    if (r == 1) {
        a_lo = mid + 1;
    } else if (r == 3) {
        a_hi = mid - 1;
    }
    while (a_lo < a_hi) {
        ll ma = a_lo + (a_hi - a_lo) / 2;
        int rr = ask(ma, bval);
        if (rr == 0) return 0;
        if (rr == 1) {
            a_lo = ma + 1;
        } else if (rr == 3) {
            a_hi = ma - 1;
        }
    }
    int final_r = ask(a_lo, bval);
    if (final_r == 0) return 0;
    return 0;
}