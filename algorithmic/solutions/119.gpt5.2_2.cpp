#include <bits/stdc++.h>
using namespace std;

using ll = long long;
static const ll MOD = 1000000007LL;

static ll mod_pow(ll a, ll e) {
    ll r = 1 % MOD;
    a %= MOD;
    while (e > 0) {
        if (e & 1) r = (r * a) % MOD;
        a = (a * a) % MOD;
        e >>= 1;
    }
    return r;
}

static ll mod_inv(ll a) {
    a %= MOD;
    if (a < 0) a += MOD;
    return mod_pow(a, MOD - 2);
}

static bool build_neutral_sequence(ll a0, int n, vector<ll>& r, vector<ll>& neu) {
    r.assign(n, 0);
    neu.assign(n, 1);
    r[0] = (a0 % MOD + MOD) % MOD;
    for (int k = 1; k <= n - 1; ++k) {
        ll cur = r[k - 1];
        if (cur == 1) return false;
        ll denom = cur - 1;
        if (denom < 0) denom += MOD;
        ll a = cur * mod_inv(denom) % MOD; // a = cur/(cur-1), ensures cur+a == cur*a
        if (a == 0) return false; // query values must be >= 1
        neu[k] = a;
        r[k] = cur * a % MOD;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<ll> r, neu;
    bool ok = false;

    // Find an initial a0 such that the neutralization sequence is well-defined up to n-1.
    for (ll s = 2; s <= 5000; ++s) {
        if (build_neutral_sequence(s, n, r, neu)) {
            ok = true;
            break;
        }
    }
    if (!ok) {
        // Extremely unlikely; still proceed with 2 to avoid undefined state.
        build_neutral_sequence(2, n, r, neu);
    }

    vector<int> op(n + 1, -1); // 0: '+', 1: '*'
    int suffixPlus = 0;        // number of '+' among positions (i+1..n) already determined

    for (int i = n; i >= 1; --i) {
        vector<ll> a(n + 1, 1);
        a[0] = r[0];
        for (int j = 1; j <= i - 1; ++j) a[j] = neu[j];

        ll rb = r[i - 1];

        ll x = 2;
        for (; x < 60; ++x) {
            ll plusv = (rb + x) % MOD;
            ll mulv = (rb * x) % MOD;
            if (plusv != mulv) break;
        }
        if (x >= 60) x = 2;
        a[i] = x;

        cout << "?";
        for (int j = 0; j <= n; ++j) cout << ' ' << a[j];
        cout << '\n' << flush;

        ll ans;
        if (!(cin >> ans)) return 0;
        if (ans < 0) return 0;

        ll expPlus = ((rb + x) % MOD + suffixPlus) % MOD;
        ll expMul  = ((rb * x) % MOD + suffixPlus) % MOD;

        if (ans == expPlus) {
            op[i] = 0;
            suffixPlus++;
        } else if (ans == expMul) {
            op[i] = 1;
        } else {
            // Fallback: deduce from removing known suffix effect.
            ll val = (ans - suffixPlus) % MOD;
            if (val < 0) val += MOD;
            if (val == (rb + x) % MOD) {
                op[i] = 0;
                suffixPlus++;
            } else {
                op[i] = 1;
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << ' ' << (op[i] == 0 ? 0 : 1);
    cout << '\n' << flush;

    return 0;
}