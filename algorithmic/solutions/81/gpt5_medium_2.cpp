#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>
using namespace std;
using boost::multiprecision::cpp_int;

long long egcd(long long a, long long b, long long &x, long long &y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long x1, y1;
    long long g = egcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

long long modinv(long long a, long long mod) {
    a %= mod; if (a < 0) a += mod;
    long long x, y;
    long long g = egcd(a, mod, x, y);
    if (g != 1) return -1;
    x %= mod;
    if (x < 0) x += mod;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    // Generate primes up to 1000
    int MAXM = 1000;
    vector<int> primes;
    vector<bool> is_prime(MAXM + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= MAXM; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (long long j = 1LL * i * i; j <= MAXM; j += i) is_prime[(int)j] = false;
        }
    }
    // Use large primes first
    sort(primes.begin(), primes.end(), greater<int>());

    vector<pair<int,int>> residues; // (mod, value)
    double sum_bits = 0.0;

    for (int p : primes) {
        if (sum_bits >= N + 2) break; // little margin
        int m = p;

        vector<int> a(m), b(m);
        for (int x = 0; x < m; ++x) {
            a[x] = (2 * x) % m;
            b[x] = (2 * x + 1) % m;
        }

        cout << 1 << "\n";
        cout << m;
        for (int i = 0; i < m; ++i) cout << ' ' << a[i];
        for (int i = 0; i < m; ++i) cout << ' ' << b[i];
        cout << "\n";
        cout.flush();

        int res;
        if (!(cin >> res)) return 0;
        residues.emplace_back(m, res);
        sum_bits += log2((double)m);
    }

    // Combine residues via CRT to reconstruct V
    cpp_int V = 0;
    cpp_int M = 1;

    for (auto &pr : residues) {
        long long m = pr.first;
        long long r = pr.second;
        long long vmod = (long long)(V % m);
        if (vmod < 0) vmod += m;
        long long t = (r - vmod) % m;
        if (t < 0) t += m;
        long long Mmod = (long long)(M % m);
        if (Mmod < 0) Mmod += m;
        long long inv = modinv(Mmod, m);
        if (inv == -1) {
            // Should not happen with coprime moduli
            inv = 0;
        }
        long long k = (long long)((__int128)t * inv % m);
        V += M * k;
        M *= m;
    }

    // Extract N bits, MSB first
    string s(N, '0');
    for (int i = N - 1; i >= 0; --i) {
        int bit = (int)(V & 1);
        s[i] = char('0' + bit);
        V >>= 1;
    }

    cout << 0 << "\n";
    cout << s << "\n";
    cout.flush();

    return 0;
}