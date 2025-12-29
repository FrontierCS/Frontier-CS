#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

ll n;
int queries_used;
map<pair<ll, ll>, ll> cache;

ll query(ll x, ll y) {
    if (x == y) return 0;
    if (x > y) swap(x, y);
    auto it = cache.find({x, y});
    if (it != cache.end()) return it->second;
    queries_used++;
    cout << "? " << x << " " << y << endl;
    ll res;
    cin >> res;
    cache[{x, y}] = res;
    return res;
}

ll getF(ll i, ll m) {
    ll j = i + m;
    if (j > n) j -= n;
    return query(i, j);
}

ll find_minimum_F(ll m) {
    // ternary search on the circle [1, n]
    ll l = 1, r = n;
    while (r - l > 10) {
        ll step = (r - l) / 3;
        ll m1 = l + step;
        ll m2 = r - step;
        ll f1 = getF(m1, m);
        ll f2 = getF(m2, m);
        if (f1 < f2) {
            r = m2;
        } else {
            l = m1;
        }
    }
    ll best_i = l;
    ll best_val = getF(l, m);
    for (ll i = l+1; i <= r; ++i) {
        ll val = getF(i, m);
        if (val < best_val) {
            best_val = val;
            best_i = i;
        }
    }
    return best_i;
}

void solve() {
    cache.clear();
    queries_used = 0;
    cin >> n;
    ll m = n / 2; // floor(n/2)
    ll i_min = find_minimum_F(m);
    ll f_min = getF(i_min, m);
    ll L = m + 1 - f_min; // shorter arc length

    // Now try to find the chord endpoints around i_min
    auto check_pair = [&](ll a, ll b) -> bool {
        if (a == b) return false;
        if (a > b) swap(a, b);
        ll diff = min(b - a, n - (b - a));
        if (diff <= 1) return false; // chord must connect non-adjacent vertices
        ll d = query(a, b);
        return d == 1;
    };

    vector<ll> candidates;
    for (ll d = -5; d <= 5; ++d) {
        ll i = i_min + d;
        if (i < 1) i += n;
        if (i > n) i -= n;
        candidates.push_back(i);
    }
    // Also consider i_min + L and i_min - L
    ll cand1 = i_min + L;
    if (cand1 > n) cand1 -= n;
    ll cand2 = i_min - L;
    if (cand2 < 1) cand2 += n;
    candidates.push_back(cand1);
    candidates.push_back(cand2);

    // Remove duplicates
    sort(candidates.begin(), candidates.end());
    candidates.erase(unique(candidates.begin(), candidates.end()), candidates.end());

    for (ll a : candidates) {
        ll b1 = a + L;
        if (b1 > n) b1 -= n;
        if (check_pair(a, b1)) {
            cout << "! " << a << " " << b1 << endl;
            int res;
            cin >> res;
            return;
        }
        ll b2 = a - L;
        if (b2 < 1) b2 += n;
        if (check_pair(a, b2)) {
            cout << "! " << a << " " << b2 << endl;
            int res;
            cin >> res;
            return;
        }
    }

    // If still not found, try a more exhaustive search (should not happen in practice)
    // We'll just try all i from 1 to n with step size to stay within query limit
    ll step = max(1LL, n / (500 - queries_used));
    for (ll i = 1; i <= n && queries_used < 500; i += step) {
        ll b = i + L;
        if (b > n) b -= n;
        if (check_pair(i, b)) {
            cout << "! " << i << " " << b << endl;
            int res;
            cin >> res;
            return;
        }
        b = i - L;
        if (b < 1) b += n;
        if (check_pair(i, b)) {
            cout << "! " << i << " " << b << endl;
            int res;
            cin >> res;
            return;
        }
    }
    // Should never reach here if the algorithm is correct
    // Make a guess anyway to avoid no output
    cout << "! 1 " << (1 + L) << endl;
    int res;
    cin >> res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}