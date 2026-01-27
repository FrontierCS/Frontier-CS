#include <bits/stdc++.h>
#include <boost/multiprecision/cpp_int.hpp>

using namespace std;
using boost::multiprecision::cpp_int;

static long long egcd(long long a, long long b, long long &x, long long &y) {
    if (b == 0) { x = 1; y = 0; return a; }
    long long x1, y1;
    long long g = egcd(b, a % b, x1, y1);
    x = y1;
    y = x1 - (a / b) * y1;
    return g;
}

static int inv_mod_int(int a, int mod) {
    long long x, y;
    long long g = egcd(a, mod, x, y);
    (void)g;
    x %= mod;
    if (x < 0) x += mod;
    return (int)x;
}

static int mod_cppint_int(const cpp_int &v, int mod) {
    return (int)((v % mod).convert_to<long long>());
}

static int query(int m) {
    std::ostringstream oss;
    oss << "1 " << m;
    for (int x = 0; x < m; x++) oss << ' ' << ((2LL * x) % m);
    for (int x = 0; x < m; x++) oss << ' ' << ((2LL * x + 1) % m);
    oss << "\n";
    cout << oss.str();
    cout.flush();

    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    const int LIM = 1002;

    vector<bool> isPrime(LIM + 1, true);
    isPrime[0] = isPrime[1] = false;
    for (int i = 2; i * 1LL * i <= LIM; i++) {
        if (!isPrime[i]) continue;
        for (int j = i * i; j <= LIM; j += i) isPrime[j] = false;
    }

    vector<int> primes;
    for (int i = 2; i <= LIM; i++) if (isPrime[i]) primes.push_back(i);

    vector<int> mods;
    mods.reserve(primes.size());
    for (int p : primes) {
        int v = 1;
        while (1LL * v * p <= LIM) v *= p;
        mods.push_back(v);
    }

    cpp_int need = cpp_int(1) << N;

    vector<pair<int,int>> used; // (mod, residue)
    used.reserve(mods.size());

    cpp_int prod = 1;
    for (int m : mods) {
        used.push_back({m, 0});
        prod *= m;
        if (prod >= need) break;
    }

    for (auto &mr : used) {
        mr.second = query(mr.first);
    }

    cpp_int x = 0;
    cpp_int M = 1;

    for (auto [m, r] : used) {
        int x_mod = mod_cppint_int(x, m);
        int M_mod = mod_cppint_int(M, m);

        int diff = r - x_mod;
        diff %= m;
        if (diff < 0) diff += m;

        int inv = inv_mod_int(M_mod, m);
        int t = (int)(1LL * diff * inv % m);

        x += M * t;
        M *= m;
    }

    // x is the value of S interpreted as an N-bit binary integer.
    string s(N, '0');
    for (int i = 0; i < N; i++) {
        int sh = N - 1 - i;
        s[i] = (((x >> sh) & 1) != 0) ? '1' : '0';
    }

    cout << "0 " << s << "\n";
    cout.flush();
    return 0;
}