#include <bits/stdc++.h>
using namespace std;
using ull = unsigned long long;
using ll = long long;

// Miller-Rabin primality test
ull mul_mod(ull a, ull b, ull mod) {
    ll ret = a * b - mod * (ull)((long double)a * b / mod);
    return ret + mod * (ret < 0) - mod * (ret >= (ll)mod);
}

ull pow_mod(ull a, ull d, ull mod) {
    ull res = 1;
    while (d) {
        if (d & 1) res = mul_mod(res, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return res;
}

bool is_prime(ull n) {
    if (n < 2) return false;
    if (n % 2 == 0) return n == 2;
    ull d = n - 1;
    int s = 0;
    while (d % 2 == 0) d >>= 1, ++s;
    for (ull a : {2, 325, 9375, 28178, 450775, 9780504, 1795265022}) {
        if (a % n == 0) continue;
        ull x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool ok = false;
        for (int r = 0; r < s - 1; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) {
                ok = true;
                break;
            }
        }
        if (!ok) return false;
    }
    return true;
}

// Pollard's Rho
ull pollard_rho(ull n) {
    if (n % 2 == 0) return 2;
    ull x = rand() % (n - 2) + 2, y = x;
    ull c = rand() % (n - 1) + 1;
    ull d = 1;
    auto f = [&](ull x) { return (mul_mod(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = __gcd(x > y ? x - y : y - x, n);
        if (d == n) return pollard_rho(n);
    }
    return d;
}

vector<ull> factorize(ull n) {
    if (n == 1) return {};
    if (is_prime(n)) return {n};
    ull d = pollard_rho(n);
    auto v1 = factorize(d), v2 = factorize(n / d);
    v1.insert(v1.end(), v2.begin(), v2.end());
    return v1;
}

// Compute bits(x) = floor(log2(x)) + 1 for x>0, 0 for x=0.
int bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Compute time for given a, d, n
ull compute_time(ull a, ull d, ull n) {
    ull r = 1;
    ull total = 0;
    for (int i = 0; i < 60; ++i) {
        if (d & (1ULL << i)) {
            total += (ull)(bits(r) + 1) * (bits(a) + 1);
            r = mul_mod(r, a, n);
        }
        total += (ull)(bits(a) + 1) * (bits(a) + 1);
        a = mul_mod(a, a, n);
    }
    return total;
}

// Modular inverse
ull inv_mod(ull a, ull m) {
    ull b = m, x = 1, y = 0;
    while (b) {
        ull t = a / b;
        a -= t * b; swap(a, b);
        x -= t * y; swap(x, y);
    }
    x %= m;
    if (x < 0) x += m;
    return x;
}

// CRT for two congruences x ≡ a1 (mod m1), x ≡ a2 (mod m2)
pair<ull, ull> crt(ull a1, ull m1, ull a2, ull m2) {
    ull g = __gcd(m1, m2);
    if ((a2 - a1) % g != 0) return {0, 0}; // no solution
    ull m = m1 / g * m2;
    ull p = inv_mod(m1 / g, m2 / g);
    ull x = (a2 - a1) % m2;
    if (x < 0) x += m2;
    x = mul_mod(x / g, p, m2 / g);
    ull res = a1 + mul_mod(x, m1, m);
    res %= m;
    if (res < 0) res += m;
    return {res, m};
}

// Find a primitive root modulo prime p
ull primitive_root(ull p) {
    vector<ull> factors;
    ull phi = p - 1;
    ull n = phi;
    for (ull f : factorize(n)) {
        if (factors.empty() || factors.back() != f)
            factors.push_back(f);
    }
    for (ull g = 2; g < p; ++g) {
        bool ok = true;
        for (ull f : factors) {
            if (pow_mod(g, phi / f, p) == 1) {
                ok = false;
                break;
            }
        }
        if (ok) return g;
    }
    return 0;
}

// Construct element of order 2^{k+1} modulo n = p*q
ull construct_element(ull p, ull q, int k) {
    // Want order 2^{k+1}
    // Try using p: find element of order 2^{k+1} mod p, and 1 mod q
    ull pp = p, qq = q;
    // Check if 2^{k+1} divides p-1
    if ((p - 1) % (1ULL << (k + 1)) == 0) {
        ull g = primitive_root(p);
        ull exponent = (p - 1) >> (k + 1);
        ull h = pow_mod(g, exponent, p);
        // CRT: x ≡ h (mod p), x ≡ 1 (mod q)
        auto [x, mod] = crt(h, p, 1, q);
        return x;
    }
    // Else try using q
    if ((q - 1) % (1ULL << (k + 1)) == 0) {
        ull g = primitive_root(q);
        ull exponent = (q - 1) >> (k + 1);
        ull h = pow_mod(g, exponent, q);
        // CRT: x ≡ 1 (mod p), x ≡ h (mod q)
        auto [x, mod] = crt(1, p, h, q);
        return x;
    }
    return 0; // cannot construct
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    ull n;
    cin >> n;

    // Factor n
    vector<ull> fac = factorize(n);
    ull p = fac[0], q = fac[1];
    if (p > q) swap(p, q);
    ull phi = (p - 1) * (q - 1);

    // Query a=1 to get popcount(d)
    cout << "? 1" << endl;
    ull time1;
    cin >> time1;
    ull popcount = time1 / 4 - 60;

    // Determine 2-adic valuations
    int v2p = __builtin_ctzll(p - 1);
    int v2q = __builtin_ctzll(q - 1);
    int max_k = max(v2p, v2q) - 1; // we can recover bits 0..max_k

    ull d_low = 0; // known lower bits
    int known_bits_count = 0;
    for (int k = 0; k <= max_k; ++k) {
        ull a = construct_element(p, q, k);
        if (a == 0) break; // cannot construct further
        cout << "? " << a << endl;
        ull T;
        cin >> T;

        // Compute expected time for d_k = 0 and d_k = 1
        // We already know bits 0..k-1 in d_low
        ull e0 = d_low; // hypothesis d_k=0
        ull e1 = d_low | (1ULL << k); // hypothesis d_k=1
        int pop_e0 = __builtin_popcountll(e0);
        int pop_e1 = pop_e0 + 1;

        // Compute r0 = a^{e0} mod n, r1 = a^{e1} mod n
        ull r0 = pow_mod(a, e0, n);
        ull r1 = pow_mod(a, e1, n);
        int bits_r0 = bits(r0);
        int bits_r1 = bits(r1);
        int bits_a0 = bits(a); // bits(a) at start (i=0)
        // Actually we need bits(a_i) for i=0..k, but for element of order 2^{k+1},
        // after i=k, a_i becomes 1. So we can compute full expected time.
        // Let's compute expected time by simulating the algorithm for the given hypothesis
        // but only up to bit k, and then add the contributions for i>k.
        // Instead, we can compute full expected time using the formula.
        // We'll compute by calling compute_time with a and the full d? But we don't know higher bits.
        // However, for the purpose of comparing hypotheses, we can assume the higher bits
        // are such that the total popcount matches popcount, and their effect on timing
        // is only via