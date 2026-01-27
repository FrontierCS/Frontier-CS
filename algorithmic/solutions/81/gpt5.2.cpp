#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static long long ext_gcd(long long a, long long b, long long &x, long long &y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long x1, y1;
    long long g = ext_gcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

static long long modinv(long long a, long long mod) {
    a %= mod;
    if (a < 0) a += mod;
    long long x, y;
    long long g = ext_gcd(a, mod, x, y);
    if (g != 1) return -1;
    x %= mod;
    if (x < 0) x += mod;
    return x;
}

static int query_mod(int m) {
    cout << 1 << "\n";
    cout << m;
    for (int x = 0; x < m; x++) {
        int ax = (2LL * x) % m;
        cout << ' ' << ax;
    }
    for (int x = 0; x < m; x++) {
        int bx = (2LL * x + 1) % m;
        cout << ' ' << bx;
    }
    cout << "\n";
    cout.flush();

    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    int LIM = 1002;
    vector<bool> is_prime(LIM + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * i <= LIM; i++) {
        if (!is_prime[i]) continue;
        for (int j = i * i; j <= LIM; j += i) is_prime[j] = false;
    }
    vector<int> primes;
    for (int i = 2; i <= LIM; i++) if (is_prime[i]) primes.push_back(i);
    sort(primes.rbegin(), primes.rend());

    cpp_int target = cpp_int(1) << N;

    cpp_int r = 0;
    cpp_int M = 1;

    int qcnt = 0;
    for (int p : primes) {
        if (M > target) break;
        if (qcnt >= 1000) break;

        int a = query_mod(p);
        qcnt++;

        long long r_mod = (long long)(r % p);
        long long t = (a - r_mod) % p;
        if (t < 0) t += p;

        long long M_mod = (long long)(M % p);
        long long inv = modinv(M_mod, p);
        long long k = (t * inv) % p;

        r += M * k;
        M *= p;
        r %= M;
    }

    // r should equal the encoded integer since M > 2^N
    cpp_int x = r;

    string s(N, '0');
    cpp_int tmp = x;
    for (int i = N - 1; i >= 0; i--) {
        s[i] = (tmp & 1) ? '1' : '0';
        tmp >>= 1;
    }

    cout << 0 << "\n" << s << "\n";
    cout.flush();
    return 0;
}