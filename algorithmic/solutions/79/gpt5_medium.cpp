#include <bits/stdc++.h>
using namespace std;

using u64 = unsigned long long;
using u128 = __uint128_t;
using i64 = long long;

// RNG
static std::mt19937_64 rng((u64)chrono::high_resolution_clock::now().time_since_epoch().count());

static inline u64 mul_mod(u64 a, u64 b, u64 mod) {
    return (u128)a * b % mod;
}
static inline u64 add_mod(u64 a, u64 b, u64 mod) {
    u64 res = a + b;
    if (res >= mod || res < a) res -= mod;
    return res;
}
static inline u64 pow_mod(u64 a, u64 e, u64 mod) {
    u64 r = 1 % mod;
    u64 x = a % mod;
    while (e) {
        if (e & 1) r = mul_mod(r, x, mod);
        x = mul_mod(x, x, mod);
        e >>= 1;
    }
    return r;
}

static bool isPrime(u64 n) {
    if (n < 2) return false;
    static u64 testPrimes[] = {2ULL,3ULL,5ULL,7ULL,11ULL,13ULL,17ULL,19ULL,23ULL,0};
    for (int i=0; testPrimes[i]; ++i) {
        if (n % testPrimes[i] == 0) return n == testPrimes[i];
    }
    u64 d = n - 1;
    int s = __builtin_ctzll(d);
    d >>= s;

    auto trial = [&](u64 a)->bool{
        if (a % n == 0) return true;
        u64 x = pow_mod(a, d, n);
        if (x == 1 || x == n-1) return true;
        for (int r=1; r<s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n-1) return true;
        }
        return false;
    };

    // Deterministic bases for 64-bit
    u64 bases[] = {2ULL, 3ULL, 5ULL, 7ULL, 11ULL, 13ULL, 17ULL, 0};
    for (int i=0; bases[i]; ++i) {
        if (!trial(bases[i])) return false;
    }
    return true;
}

static u64 pollard_rho(u64 n) {
    if ((n & 1ULL) == 0ULL) return 2;
    if (n % 3ULL == 0ULL) return 3;
    u64 c = uniform_int_distribution<u64>(1, n-1)(rng);
    u64 x = uniform_int_distribution<u64>(0, n-1)(rng);
    u64 y = x;
    u64 d = 1;
    auto f = [&](u64 v)->u64 { return add_mod(mul_mod(v, v, n), c, n); };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        u64 diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
        if (d == n) {
            // retry with different parameters
            c = uniform_int_distribution<u64>(1, n-1)(rng);
            x = uniform_int_distribution<u64>(0, n-1)(rng);
            y = x;
            d = 1;
        }
    }
    return d;
}

static void factor(u64 n, vector<u64>& fac) {
    if (n == 1) return;
    if (isPrime(n)) { fac.push_back(n); return; }
    u64 d = n;
    while (d == n) d = pollard_rho(n);
    factor(d, fac);
    factor(n/d, fac);
}

static inline int bits64(u64 x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

static u64 inv_mod(u64 a, u64 mod) {
    // Extended Euclid
    i64 t = 0, newt = 1;
    i64 r = (i64)mod, newr = (i64)(a % mod);
    while (newr != 0) {
        i64 q = r / newr;
        i64 tmp = t - q * newt; t = newt; newt = tmp;
        tmp = r - q * newr; r = newr; newr = tmp;
    }
    if (r > 1) return 0; // not invertible
    if (t < 0) t += (i64)mod;
    return (u64)t;
}

static u64 crt_combine(u64 ap, u64 p, u64 aq, u64 q) {
    // x ≡ ap (mod p), x ≡ aq (mod q)
    u64 invp = inv_mod(p % q, q);
    u64 t = (aq + q - (ap % q)) % q;
    u64 k = mul_mod(t, invp, q);
    u128 x = (u128)ap + (u128)k * p;
    u64 n = p * q;
    u64 res = (u64)(x % n);
    return res;
}

static u64 find_max2_element(u64 prime) {
    u64 p = prime;
    u64 m = p - 1;
    int v = __builtin_ctzll(m);
    if (v == 0) return 1; // shouldn't happen for odd prime
    u64 odd = m >> v;
    while (true) {
        u64 g = uniform_int_distribution<u64>(2, p-2)(rng);
        u64 y = pow_mod(g, odd, p);
        if (y == 1) continue;
        u64 z = y;
        // Check y^(2^{v-1}) == -1
        z = pow_mod(y, 1ULL << (v-1), p);
        if (z == p - 1) return y;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    u64 n;
    if (!(cin >> n)) {
        return 0;
    }

    // Factor n
    vector<u64> fac;
    factor(n, fac);
    sort(fac.begin(), fac.end());
    // Expect two primes
    u64 p = fac[0], q = fac[1];
    if (p * q != n) {
        // In rare case pollard returns duplicates, adjust
        // Aggregate equal primes
        u64 a = fac[0];
        for (size_t i=1;i<fac.size();++i) a *= fac[i];
        // Not expected in problem constraints - but we proceed
        // Try to get two primes from factors
        // If more than two, combine to two by multiplying
        u64 prod = 1;
        for (auto f: fac) {
            if (isPrime(f)) {
                if (prod == 1) prod = f;
                else { if (p==0) p = prod, prod = f; }
            }
        }
        // Fallback
        p = fac[0];
        q = n / p;
    }
    if (p > q) swap(p, q);

    int vp = __builtin_ctzll(p - 1);
    int vq = __builtin_ctzll(q - 1);
    int t = max(vp, vq);
    // Build g of order 2^t
    u64 g;
    if (vp >= vq) {
        u64 xp = find_max2_element(p); // order 2^vp
        // Set g ≡ xp mod p, ≡ 1 mod q
        g = crt_combine(xp % p, p, 1 % q, q);
    } else {
        u64 xq = find_max2_element(q); // order 2^vq
        // Set g ≡ 1 mod p, ≡ xq mod q
        g = crt_combine(1 % p, p, xq % q, q);
    }

    auto query = [&](u64 a)->u64 {
        cout << "? " << a << "\n";
        cout.flush();
        u64 T;
        cin >> T;
        return T;
    };

    // Query a=1 to get popcount s
    u64 T1 = query(1 % n);
    u64 sumSquares1 = 0;
    {
        u64 a = 1 % n;
        for (int i=0;i<60;++i) {
            int ba = bits64(a);
            sumSquares1 += (u64)(ba + 1) * (u64)(ba + 1);
            a = mul_mod(a, a, n);
        }
    }
    u64 s = (T1 - sumSquares1) / 4ULL;

    vector<int> d_bits(60, 0);
    u64 ones_lo = 0;

    for (int k = 0; k < 60; ++k) {
        u64 a0;
        int eshift = t - (k + 1);
        if (eshift >= 0) {
            a0 = pow_mod(g, 1ULL << eshift, n);
        } else {
            a0 = g % n;
        }

        u64 T = query(a0);

        // Compute sumSquares for this a0
        u64 sumSquares = 0;
        {
            u64 a = a0;
            for (int i=0;i<60;++i) {
                int ba = bits64(a);
                sumSquares += (u64)(ba + 1) * (u64)(ba + 1);
                a = mul_mod(a, a, n);
            }
        }

        // Compute contributions from known bits < k and get R0, a_k
        u64 sumPrev = 0;
        u64 r = 1 % n;
        u64 a = a0;
        for (int i=0;i<k;++i) {
            if (d_bits[i]) {
                int br = bits64(r);
                int ba = bits64(a);
                sumPrev += (u64)(br + 1) * (u64)(ba + 1);
                r = mul_mod(r, a, n);
            }
            a = mul_mod(a, a, n);
        }
        u64 a_k = a;
        u64 R0 = r;

        u64 pop_hi_0 = s - ones_lo;         // number of ones among indices >= k
        u64 T0pred = sumSquares + sumPrev + pop_hi_0 * 2ULL * (u64)(bits64(R0) + 1);

        u64 cost_k = (u64)(bits64(R0) + 1) * (u64)(bits64(a_k) + 1);
        u64 R1 = mul_mod(R0, a_k, n);
        u64 pop_hi_1 = (s >= ones_lo + 1 ? s - ones_lo - 1 : 0);
        u64 T1pred = sumSquares + sumPrev + cost_k + pop_hi_1 * 2ULL * (u64)(bits64(R1) + 1);

        if (T == T1pred) {
            d_bits[k] = 1;
            ones_lo++;
        } else {
            d_bits[k] = 0;
        }
    }

    // Reconstruct d
    u64 d = 0;
    for (int i=0;i<60;++i) {
        if (d_bits[i]) d |= (1ULL << i);
    }

    cout << "! " << d << "\n";
    cout.flush();
    return 0;
}