#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

int modInverse(int a, int mod) {
    int b = mod, u = 1, v = 0;
    while (b) {
        int t = a / b;
        a -= t * b; swap(a, b);
        u -= t * v; swap(u, v);
    }
    u %= mod;
    if (u < 0) u += mod;
    return u;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    const int LIMIT = 1000;
    vector<int> primes;
    vector<bool> isPrime(LIMIT + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; i * i <= LIMIT; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j <= LIMIT; j += i) {
                isPrime[j] = false;
            }
        }
    }
    for (int i = 2; i <= LIMIT; ++i) {
        if (isPrime[i]) primes.push_back(i);
    }

    vector<int> mods;
    double logSum = 0.0;
    for (int p : primes) {
        mods.push_back(p);
        logSum += log2((long double)p);
        if (logSum >= N) break;
    }

    int Qcnt = (int)mods.size();
    vector<int> residues;
    residues.reserve(Qcnt);

    for (int idx = 0; idx < Qcnt; ++idx) {
        int m = mods[idx];
        vector<int> a(m), b(m);
        for (int x = 0; x < m; ++x) {
            a[x] = (2 * x) % m;
            b[x] = (2 * x + 1) % m;
        }

        cout << 1 << '\n';
        cout << m << '\n';
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << a[i];
        }
        cout << '\n';
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << b[i];
        }
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x < 0) return 0;  // in case of judge error signal
        residues.push_back(x % m);
    }

    // Chinese Remainder Theorem to reconstruct the integer Q
    cpp_int R = 0;
    cpp_int M = 1;
    for (int i = 0; i < Qcnt; ++i) {
        int p = mods[i];
        int r = residues[i];
        cpp_int cp = p;

        cpp_int tM = M % cp;
        int M_mod_p = tM.convert_to<int>();

        cpp_int tR = R % cp;
        int R_mod_p = tR.convert_to<int>();

        int delta = r - R_mod_p;
        delta %= p;
        if (delta < 0) delta += p;

        int inv = modInverse(M_mod_p, p);
        int k = (int)((1LL * delta * inv) % p);

        cpp_int ck = k;
        R += M * ck;
        M *= cp;
    }

    cpp_int q = R;
    string s(N, '0');
    for (int i = N - 1; i >= 0; --i) {
        int bit = (q & 1).convert_to<int>();
        s[i] = char('0' + bit);
        q >>= 1;
    }

    cout << 0 << '\n';
    cout << s << '\n';
    cout.flush();

    return 0;
}