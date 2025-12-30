#include <bits/stdc++.h>
using namespace std;

using ll = long long;
using ld = long double;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct CustomHashLL {
    size_t operator()(ll x) const {
        static const uint64_t FIXED_RANDOM =
            chrono::steady_clock::now().time_since_epoch().count();
        return (size_t)splitmix64((uint64_t)x + FIXED_RANDOM);
    }
};

struct Interactor {
    ll qcnt = 0;

    ld query(ll x, ll y) {
        ++qcnt;
        cout << "? " << x << " " << y << "\n" << flush;
        ld ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    }
};

static inline ll floor_div(ll a, ll b) {
    // b > 0
    if (a >= 0) return a / b;
    return - ( ( -a + b - 1 ) / b );
}

static inline ll ceil_div(ll a, ll b) {
    // b > 0
    return -floor_div(-a, b);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    Interactor it;

    const ll X0 = 20001; // > 20000 guarantees all y_i = a_i*X0 + b_i are distinct
    const ll LIM = 10000;

    const ll maxY = LIM * llabs(X0) + LIM; // max |a*X0 + b|
    const ll L = -maxY - 5;
    const ll R =  maxY + 5; // inclusive bound for g(y) cache; D(k) uses g(k), g(k+1) so needs up to R

    unordered_map<ll, ld, CustomHashLL> gcache;
    unordered_map<ll, ld, CustomHashLL> dcache;

    auto g = [&](ll y) -> ld {
        auto itc = gcache.find(y);
        if (itc != gcache.end()) return itc->second;
        ld val = it.query(X0, y);
        gcache.emplace(y, val);
        return val;
    };

    auto D = [&](ll k) -> ld {
        // D(k) = g(k+1) - g(k), k in [L, R-1]
        auto itd = dcache.find(k);
        if (itd != dcache.end()) return itd->second;
        ld val = g(k + 1) - g(k);
        dcache.emplace(k, val);
        return val;
    };

    const ld EPS = 1e-5L;

    auto firstGreater = [&](ll lo, ll hi, ld cur) -> ll {
        // smallest k in [lo, hi] with D(k) > cur + EPS; if none returns hi+1
        ll l = lo, r = hi + 1;
        while (l < r) {
            ll m = l + (r - l) / 2;
            if (D(m) > cur + EPS) r = m;
            else l = m + 1;
        }
        return l;
    };

    vector<ll> ys;
    ys.reserve(n);

    ll k = L;
    ld cur = D(k);

    while ((int)ys.size() < n) {
        ll pos = firstGreater(k, R - 1, cur);
        if (pos >= R) break;
        ys.push_back(pos);
        cur = D(pos);
        k = pos;
    }

    vector<ll> a(n), b(n);

    for (int i = 0; i < n; i++) {
        ll y = ys[i];

        // Unique a such that b = y - a*X0 in [-LIM, LIM]
        ll al = ceil_div(y - LIM, X0);
        ll ah = floor_div(y + LIM, X0);

        ll ai;
        if (al == ah) {
            ai = al;
        } else {
            // Fallback (shouldn't happen): search near rounded value
            ll approx = (ll) llround((long double)y / (long double)X0);
            bool ok = false;
            for (ll da = -3; da <= 3; da++) {
                ll cand = approx + da;
                ll bb = y - cand * X0;
                if (-LIM <= cand && cand <= LIM && -LIM <= bb && bb <= LIM) {
                    ai = cand;
                    ok = true;
                    break;
                }
            }
            if (!ok) ai = approx;
        }

        ll bi = y - ai * X0;

        a[i] = ai;
        b[i] = bi;
    }

    cout << "! ";
    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << a[i];
    }
    for (int i = 0; i < n; i++) {
        cout << ' ' << b[i];
    }
    cout << "\n" << flush;

    return 0;
}