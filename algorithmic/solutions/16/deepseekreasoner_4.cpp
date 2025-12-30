#include <bits/stdc++.h>
using namespace std;
using ll = long long;

ll query(ll x, ll y) {
    cout << "? " << x << ' ' << y << endl;
    ll res;
    cin >> res;
    return res;
}

void guess(ll u, ll v) {
    cout << "! " << u << ' ' << v << endl;
    int r;
    cin >> r;
    if (r == -1) exit(0);
}

int main() {
    int T;
    cin >> T;
    while (T--) {
        ll n;
        cin >> n;

        // Check if vertex 1 is an endpoint of the chord
        bool found = false;
        for (ll i = 3; i <= min(n, 50LL); ++i) {
            ll d = query(1, i);
            if (d == 1) {
                guess(1, i);
                found = true;
                break;
            }
        }
        if (found) continue;

        // Binary search for the first vertex i (>1) where the distance from 1
        // differs from the pure cycle distance.
        ll low = 2, high = n, p = n;
        while (low < high) {
            ll mid = (low + high) / 2;
            ll d = query(1, mid);
            ll baseline = min(mid - 1, n - mid + 1);
            if (d != baseline) {
                high = mid;
                p = mid;
            } else {
                low = mid + 1;
            }
        }
        p = low;
        ll dist = query(1, p);
        ll a = dist, b = p;
        if (a > b) swap(a, b);
        guess(a, b);
    }
    return 0;
}