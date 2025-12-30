#include <bits/stdc++.h>
using namespace std;

using ll = long long;

const ll MOD = 1000000007LL;
const ll PHI = MOD - 1;

ll mod_pow(ll a, ll e) {
    ll r = 1 % MOD;
    a %= MOD;
    while (e > 0) {
        if (e & 1) r = (__int128)r * a % MOD;
        a = (__int128)a * a % MOD;
        e >>= 1;
    }
    return r;
}

ll primitive_root() {
    ll phi = PHI;
    vector<ll> fac;
    ll n = phi;
    for (ll p = 2; p * p <= n; ++p) {
        if (n % p == 0) {
            fac.push_back(p);
            while (n % p == 0) n /= p;
        }
    }
    if (n > 1) fac.push_back(n);
    for (ll g = 2; g < MOD; ++g) {
        bool ok = true;
        for (ll q : fac) {
            if (mod_pow(g, phi / q) == 1) {
                ok = false;
                break;
            }
        }
        if (ok) return g;
    }
    return -1;
}

unordered_map<ll,int> baby;
int M_bsgs;
ll g_root;
ll factor_inv_m;

void init_bsgs(ll g) {
    g_root = g;
    M_bsgs = (int)(sqrt((long double)PHI) + 1);
    baby.reserve(M_bsgs * 2);
    baby.max_load_factor(0.7f);
    ll cur = 1 % MOD;
    for (int i = 0; i < M_bsgs; ++i) {
        if (!baby.count(cur)) baby[cur] = i;
        cur = (__int128)cur * g_root % MOD;
    }
    factor_inv_m = mod_pow(g_root, PHI - (M_bsgs % PHI)); // g^{-M_bsgs}
}

ll discrete_log(ll y) {
    y %= MOD;
    if (y == 1) return 0;
    ll cur = y;
    for (int j = 0; j <= M_bsgs; ++j) {
        auto it = baby.find(cur);
        if (it != baby.end()) {
            ll x = (ll)j * M_bsgs + it->second;
            x %= PHI;
            return x;
        }
        cur = (__int128)cur * factor_inv_m % MOD;
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    ll g = primitive_root();
    init_bsgs(g);

    const int K = 29; // group size
    vector<int> op(n + 1, 0); // 0 for '+', 1 for '×'
    vector<ll> a(n + 1);

    auto ask = [&](ll a0, const vector<ll> &vec) -> ll {
        cout << "? " << a0;
        for (int i = 1; i <= n; ++i) {
            cout << ' ' << vec[i];
        }
        cout << '\n';
        cout.flush();
        ll res;
        if (!(cin >> res)) exit(0);
        return res;
    };

    int groups = (n + K - 1) / K;
    for (int gid = 0; gid < groups; ++gid) {
        int L = gid * K + 1;
        int R = min(n, (gid + 1) * K);
        int sz = R - L + 1;

        for (int i = 1; i <= n; ++i) {
            if (i >= L && i <= R) {
                int k = i - L; // 0-based in group
                ll exp = 1LL << k; // 2^k
                a[i] = mod_pow(g, exp);
            } else {
                a[i] = 1;
            }
        }

        ll ans1 = ask(1, a);
        ll ans2 = ask(2, a);
        ll A = ans2 - ans1;
        if (A < 0) A += MOD;

        ll e;
        if (A == 1) {
            e = 0;
        } else {
            e = discrete_log(A);
            if (e < 0) e += PHI;
        }

        for (int k = 0; k < sz; ++k) {
            int idx = L + k;
            int bit = (int)((e >> k) & 1LL);
            op[idx] = bit;
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << op[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}