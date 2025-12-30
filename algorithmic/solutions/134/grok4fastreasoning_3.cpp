#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

ll n;
vector<pair<ll, ll>> forbids;
ll la, lb;

bool is_possible_a(ll cand) {
    if (cand < la || cand > n) return false;
    ll miny = LLONG_MAX / 2;
    for (auto [xi, yi] : forbids) {
        if (xi <= cand) miny = min(miny, yi);
    }
    ll maxb = (miny == LLONG_MAX / 2 ? n : miny - 1);
    return maxb >= lb && maxb <= n;
}

ll get_max_a() {
    ll low = la, high = n;
    ll ans = la - 1;
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        if (is_possible_a(mid)) {
            ans = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return ans;
}

bool is_possible_b(ll cand) {
    if (cand < lb || cand > n) return false;
    ll minx = LLONG_MAX / 2;
    for (auto [xi, yi] : forbids) {
        if (yi <= cand) minx = min(minx, xi);
    }
    ll maxa = (minx == LLONG_MAX / 2 ? n : minx - 1);
    return maxa >= la && maxa <= n;
}

ll get_max_b() {
    ll low = lb, high = n;
    ll ans = lb - 1;
    while (low <= high) {
        ll mid = low + (high - low) / 2;
        if (is_possible_b(mid)) {
            ans = mid;
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    return ans;
}

int ask(ll x, ll y) {
    cout << x << " " << y << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == 0) exit(0);
    return res;
}

int main() {
    cin >> n;
    la = 1;
    lb = 1;
    forbids.clear();
    while (true) {
        ll cura = get_max_a();
        ll curb = get_max_b();
        if (cura < la || curb < lb) {
            assert(false);
        }
        if (cura == la && curb == lb) {
            ask(la, lb);
            return 0;
        }
        if (cura == la) {
            // fix a = la, binary search b
            ll aa = la;
            ll miny = LLONG_MAX / 2;
            for (auto p : forbids) {
                if (p.first <= aa) miny = min(miny, p.second);
            }
            ll maxb = (miny == LLONG_MAX / 2 ? n : miny - 1);
            ll l = lb;
            ll r = min(n, maxb);
            if (l > r) assert(false);
            while (l < r) {
                ll my = l + (r - l + 1) / 2;
                int res = ask(aa, my);
                if (res == 0) return 0;
                if (res == 2) {
                    l = my + 1;
                } else {
                    r = my - 1;
                }
            }
            ask(aa, l);
            return 0;
        }
        if (curb == lb) {
            // fix b = lb, binary search a
            ll bb = lb;
            ll minx = LLONG_MAX / 2;
            for (auto p : forbids) {
                if (p.second <= bb) minx = min(minx, p.first);
            }
            ll maxa = (minx == LLONG_MAX / 2 ? n : minx - 1);
            ll l = la;
            ll r = min(n, maxa);
            if (l > r) assert(false);
            while (l < r) {
                ll mx = l + (r - l + 1) / 2;
                int res = ask(mx, bb);
                if (res == 0) return 0;
                if (res == 1) {
                    l = mx + 1;
                } else {
                    r = mx - 1;
                }
            }
            ask(l, bb);
            return 0;
        }
        // joint query
        ll mx = la + (cura - la) / 2;
        ll my = lb + (curb - lb) / 2;
        mx = max(1LL, min(n, mx));
        my = max(1LL, min(n, my));
        int res = ask(mx, my);
        if (res == 1) {
            la = mx + 1;
        } else if (res == 2) {
            lb = my + 1;
        } else if (res == 3) {
            forbids.emplace_back(mx, my);
        }
    }
    return 0;
}