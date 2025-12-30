#include <bits/stdc++.h>
using namespace std;
typedef long long ll;
const ll MOD = 1000000007LL;

ll modpow(ll b, ll e, ll mod) {
    ll res = 1;
    b %= mod;
    while (e > 0) {
        if (e & 1) res = (res * b) % mod;
        b = (b * b) % mod;
        e >>= 1;
    }
    return res;
}

ll modinv(ll x, ll mod) {
    return modpow(x, mod - 2, mod);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int n;
    cin >> n;
    vector<int> is_mult(n + 1, -1);
    for (int kk = n; kk >= 1; --kk) {
        int maxs = kk;
        ll chosen_ak = -1;
        bool found_ak = false;
        for (ll ak_cand = (ll)maxs + 1; ak_cand < MOD && !found_ak; ++ak_cand) {
            ll inv = modinv(ak_cand, MOD);
            bool ok = true;
            for (int ss = 1; ss <= maxs && ok; ++ss) {
                ll tempv = ((ll)ss + ak_cand) % MOD;
                ll sstar = tempv * inv % MOD;
                if (sstar >= 1 && sstar <= (ll)maxs) ok = false;
            }
            if (ok) {
                chosen_ak = ak_cand;
                found_ak = true;
            }
        }
        assert(found_ak);
        int tt = 0;
        for (int j = kk + 1; j <= n; ++j) {
            if (is_mult[j] == 0) ++tt;
        }
        vector<ll> qa(n + 1, 1LL);
        qa[kk] = chosen_ak;
        cout << "?";
        for (int i = 0; i <= n; ++i) {
            cout << " " << qa[i];
        }
        cout << "\n";
        cout.flush();
        ll rr;
        cin >> rr;
        ll temp = (rr - (ll)tt + MOD) % MOD;
        // +
        ll sp = (temp - chosen_ak + MOD) % MOD;
        bool vp = (sp >= 1 && sp <= (ll)maxs);
        // *
        ll invak = modinv(chosen_ak, MOD);
        ll ss_ = temp * invak % MOD;
        bool vs = (ss_ >= 1 && ss_ <= (ll)maxs) && ((ss_ * chosen_ak % MOD) == temp);
        if (vp && vs) {
            assert(false);
        } else if (vp) {
            is_mult[kk] = 0;
        } else if (vs) {
            is_mult[kk] = 1;
        } else {
            assert(false);
        }
    }
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << is_mult[i];
    }
    cout << "\n";
    cout.flush();
    return 0;
}