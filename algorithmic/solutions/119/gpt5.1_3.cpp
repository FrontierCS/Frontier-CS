#include <bits/stdc++.h>
using namespace std;

const long long MOD = 1000000007LL;

long long mod_pow(long long a, long long e) {
    long long r = 1 % MOD;
    while (e > 0) {
        if (e & 1) r = (__int128)r * a % MOD;
        a = (__int128)a * a % MOD;
        e >>= 1;
    }
    return r;
}

long long primitive_root(long long mod) {
    long long phi = mod - 1;
    long long n = phi;
    vector<long long> factors;
    for (long long i = 2; i * i <= n; ++i) {
        if (n % i == 0) {
            factors.push_back(i);
            while (n % i == 0) n /= i;
        }
    }
    if (n > 1) factors.push_back(n);
    for (long long g = 2; ; ++g) {
        bool ok = true;
        for (long long p : factors) {
            if (mod_pow(g, phi / p) == 1) {
                ok = false;
                break;
            }
        }
        if (ok) return g;
    }
}

// BSGS for exponents up to Emax (known small bound)
struct BSGS {
    long long g, MOD, Emax, m, gm_inv;
    unordered_map<long long, int> baby;

    void init(long long _g, long long _MOD, long long _Emax) {
        g = _g; MOD = _MOD; Emax = _Emax;
        long double sd = sqrt((long double)(Emax + 1));
        m = (long long)sd + 1; // m > sqrt(Emax+1)
        baby.reserve(m * 2);
        baby.max_load_factor(0.7f);
        long long e = 1;
        for (int j = 0; j < m; ++j) {
            if (!baby.count(e)) baby[e] = j;
            e = (__int128)e * g % MOD;
        }
        long long exp = (MOD - 1 - (m % (MOD - 1))) % (MOD - 1);
        gm_inv = mod_pow(g, exp); // g^{-m}
    }

    long long log(long long A) {
        A %= MOD;
        if (A == 1) return 0;
        long long cur = A;
        long long max_i = Emax / m + 1;
        for (long long i = 0; i <= max_i; ++i) {
            auto it = baby.find(cur);
            if (it != baby.end()) {
                long long x = i * m + it->second;
                if (x <= Emax) return x;
            }
            cur = (__int128)cur * gm_inv % MOD;
        }
        return -1; // should not happen
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    long long g = primitive_root(MOD);

    int L;
    if (n <= 28) L = n;
    else L = 29;
    long long Emax = (1LL << L) - 1;

    BSGS solver;
    solver.init(g, MOD, Emax);

    vector<int> op(n + 1, 0);
    int groups = (n + L - 1) / L;

    for (int gi = 0; gi < groups; ++gi) {
        int l = gi * L + 1;
        int r = min(n, l + L - 1);
        int len = r - l + 1;

        vector<long long> a(n + 1);
        for (int i = 1; i <= n; ++i) {
            long long exp = 0;
            if (i >= l && i <= r) {
                int pos = i - l;
                exp = 1LL << pos;
            }
            if (exp == 0) a[i] = 1;
            else a[i] = mod_pow(g, exp);
        }

        auto ask = [&](long long a0) -> long long {
            cout << "? " << a0;
            for (int i = 1; i <= n; ++i) {
                cout << ' ' << a[i];
            }
            cout << endl;
            cout.flush();
            long long res;
            if (!(cin >> res)) exit(0);
            return res;
        };

        long long res1 = ask(1);
        long long res2 = ask(2);

        long long A = res2 - res1;
        A %= MOD;
        if (A < 0) A += MOD;

        long long e = solver.log(A);
        if (e < 0) e = 0; // fallback, should not happen

        for (int pos = 0; pos < len; ++pos) {
            int idx = l + pos;
            int bit = (e >> pos) & 1;
            op[idx] = bit;
        }
    }

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << op[i];
        if (i < n) cout << ' ';
    }
    cout << endl;
    cout.flush();

    return 0;
}