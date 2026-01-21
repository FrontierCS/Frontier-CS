#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>
using namespace std;
using boost::multiprecision::cpp_int;

long long extgcd(long long a, long long b, long long &x, long long &y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long x1, y1;
    long long g = extgcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}
long long modinv(long long a, long long m) {
    long long x, y;
    long long g = extgcd((a % m + m) % m, m, x, y);
    if (g != 1) return 0; // should not happen for coprime
    x %= m;
    if (x < 0) x += m;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    // Sieve primes up to 1000
    const int LIM = 1000;
    vector<bool> isprime(LIM + 1, true);
    isprime[0] = isprime[1] = false;
    for (int i = 2; i * i <= LIM; ++i) {
        if (isprime[i]) {
            for (int j = i * i; j <= LIM; j += i) isprime[j] = false;
        }
    }
    vector<int> primes;
    for (int i = 2; i <= LIM; ++i) if (isprime[i]) primes.push_back(i);

    // Choose largest primes until total bits exceed N
    vector<int> selected;
    double bits = 0.0;
    for (int i = (int)primes.size() - 1; i >= 0; --i) {
        selected.push_back(primes[i]);
        bits += log2((double)primes[i]);
        if (bits > N + 2) break;
    }
    // As a fallback, if not enough (shouldn't happen), use all primes
    if (bits <= N + 2) {
        selected = primes;
    }

    cpp_int res = 0;
    cpp_int modprod = 1;

    for (int p : selected) {
        // Prepare a and b for base-2 rolling hash: a[x] = (2x) mod p, b[x] = (2x+1) mod p
        cout << 1 << '\n';
        cout << p << '\n';
        for (int x = 0; x < p; ++x) {
            int val = (2 * x) % p;
            if (x) cout << ' ';
            cout << val;
        }
        cout << '\n';
        for (int x = 0; x < p; ++x) {
            int val = (2 * x + 1) % p;
            if (x) cout << ' ';
            cout << val;
        }
        cout << '\n';
        cout.flush();

        int xr;
        if (!(cin >> xr)) return 0;
        if (xr < 0) return 0; // interactor error

        long long mpmod = (long long)(modprod % p);
        long long rem = (long long)(res % p);
        long long t = xr - rem;
        t %= p;
        if (t < 0) t += p;
        long long inv = modinv(mpmod, p);
        long long add = (long long)(((__int128)t * inv) % p);

        res += modprod * add;
        modprod *= p;
    }

    // Convert res to N-bit binary string (MSB first, S_0 ... S_{N-1})
    string s(N, '0');
    cpp_int val = res;
    for (int i = N - 1; i >= 0; --i) {
        int bit = (int)(val & 1);
        s[i] = char('0' + bit);
        val >>= 1;
    }

    cout << 0 << '\n';
    cout << s << '\n';
    cout.flush();

    return 0;
}