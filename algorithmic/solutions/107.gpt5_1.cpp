#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;

u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}

u64 pow_mod(u64 a, u64 d, u64 mod) {
    u64 r = 1;
    while (d) {
        if (d & 1) r = mul_mod(r, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return r;
}

bool isPrime64(u64 n) {
    if (n < 2) return false;
    for (u64 p : {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL}) {
        if (n % p == 0) return n == p;
    }
    u64 d = n - 1, s = 0;
    while ((d & 1) == 0) { d >>= 1; ++s; }
    // Deterministic bases for 64-bit
    const u64 bases[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL};
    for (u64 a : bases) {
        if (a % n == 0) continue;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool comp = true;
        for (u64 r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) { comp = false; break; }
        }
        if (comp) return false;
    }
    return true;
}

u64 pollard(u64 n) {
    if (n % 2ULL == 0ULL) return 2ULL;
    static std::mt19937_64 rng((u64)chrono::steady_clock::now().time_since_epoch().count());
    while (true) {
        u64 c = rng() % (n - 1) + 1;
        u64 x = rng() % (n - 2) + 2;
        u64 y = x;
        u64 d = 1;
        auto f = [&](u64 v) { return (mul_mod(v, v, n) + c) % n; };
        while (d == 1) {
            x = f(x);
            y = f(f(y));
            u64 diff = x > y ? x - y : y - x;
            d = std::gcd(diff, n);
        }
        if (d != n) return d;
    }
}

void factor_rec(u64 n, map<u64, int>& mp);

void factor_large(u64 n, map<u64, int>& mp) {
    if (n == 1) return;
    if (isPrime64(n)) { mp[n]++; return; }
    u64 d = pollard(n);
    factor_rec(d, mp);
    factor_rec(n / d, mp);
}

const int MAXP = 1000000;
vector<int> small_primes;

void sieve() {
    vector<bool> is_prime(MAXP + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i * 1LL * i <= MAXP; ++i) {
        if (is_prime[i]) {
            for (long long j = 1LL * i * i; j <= MAXP; j += i) is_prime[(int)j] = false;
        }
    }
    for (int i = 2; i <= MAXP; ++i) if (is_prime[i]) small_primes.push_back(i);
}

void factor_rec(u64 n, map<u64, int>& mp) {
    if (n == 1) return;
    for (int p : small_primes) {
        u64 pp = (u64)p;
        if (pp * pp > n) break;
        if (n % pp == 0) {
            int cnt = 0;
            while (n % pp == 0) { n /= pp; ++cnt; }
            mp[pp] += cnt;
        }
    }
    if (n == 1) return;
    if (isPrime64(n)) { mp[n]++; return; }
    factor_large(n, mp);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    sieve();
    
    int T;
    if (!(cin >> T)) return 0;
    for (int _ = 0; _ < T; ++_) {
        u64 x;
        if (!(cin >> x)) x = 0;
        map<u64, int> mp;
        factor_rec(x, mp);
        unsigned long long ans = 1;
        for (auto &kv : mp) {
            ans *= (unsigned long long)(kv.second + 1);
        }
        cout << ans << "\n";
    }
    return 0;
}