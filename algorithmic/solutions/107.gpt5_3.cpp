#include <bits/stdc++.h>
using namespace std;

using u64 = uint64_t;
using u128 = __uint128_t;

u64 mod_mul(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 mod_pow(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mod_mul(r, a, mod);
        a = mod_mul(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,0};
    for (u64 p : testPrimes) {
        if (p == 0) break;
        if (n%p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    auto trial = [&](u64 a)->bool{
        if (a % n == 0) return true;
        u64 x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) return true;
        for (u64 r = 1; r < s; ++r) {
            x = mod_mul(x, x, n);
            if (x == n - 1) return true;
        }
        return false;
    };
    // Deterministic bases for 64-bit integers
    u64 bases[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 0ULL};
    for (u64 a : bases) {
        if (a == 0) break;
        if (!trial(a)) return false;
    }
    return true;
}

mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

u64 pollard(u64 n) {
    if ((n & 1ULL) == 0) return 2;
    if (isPrime(n)) return n;
    while (true) {
        u64 c = uniform_int_distribution<u64>(1, n - 1)(rng);
        u64 x = uniform_int_distribution<u64>(2, n - 2)(rng);
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v){ return (mod_mul(v, v, n) + c) % n; };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
            if (d == n) break;
        }
        if (d > 1 && d < n) return d;
    }
}

void factor(u64 n, unordered_map<u64,int>& mp) {
    if (n == 1) return;
    if (isPrime(n)) { mp[n]++; return; }
    u64 d = pollard(n);
    factor(d, mp);
    factor(n / d, mp);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        u64 X;
        if (!(cin >> X)) X = 0;
        if (X == 0) { cout << 0 << "\n"; continue; }
        unordered_map<u64,int> mp;
        factor(X, mp);
        unsigned long long ans = 1;
        for (auto &kv : mp) {
            ans *= (unsigned long long)(kv.second + 1);
        }
        cout << ans << "\n";
    }
    return 0;
}