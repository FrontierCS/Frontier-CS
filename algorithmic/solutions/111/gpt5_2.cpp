#include <bits/stdc++.h>
using namespace std;

using u32 = uint32_t;
using u64 = uint64_t;

int poly_deg(u32 a) { return a ? 31 - __builtin_clz(a) : -1; }

u32 poly_rem(u32 a, u32 b) {
    int db = poly_deg(b);
    if (db < 0) return a;
    while (a && poly_deg(a) >= db) {
        int shift = poly_deg(a) - db;
        a ^= (b << shift);
    }
    return a;
}

u32 poly_gcd(u32 a, u32 b) {
    while (b) {
        u32 r = poly_rem(a, b);
        a = b;
        b = r;
    }
    return a;
}

u32 gf_mul(u32 a, u32 b, u32 mod, int d) {
    u32 res = 0;
    while (b) {
        if (b & 1u) res ^= a;
        b >>= 1;
        a <<= 1;
        if (a & (1u << d)) a ^= mod;
    }
    return res;
}

bool is_irreducible(u32 f, int d) {
    if (d <= 0) return false;
    // x^(2^d) mod f should equal x
    u32 x = 2; // polynomial 'x'
    u32 xp = x;
    for (int i = 0; i < d; ++i) xp = gf_mul(xp, xp, f, d);
    if (xp != x) return false;

    // Factor d to primes
    vector<int> primes;
    int tmp = d;
    for (int p = 2; p * p <= tmp; ++p) {
        if (tmp % p == 0) {
            primes.push_back(p);
            while (tmp % p == 0) tmp /= p;
        }
    }
    if (tmp > 1) primes.push_back(tmp);

    for (int p : primes) {
        int e = d / p;
        u32 t = x;
        for (int i = 0; i < e; ++i) t = gf_mul(t, t, f, d); // x^(2^e) mod f
        u32 g = poly_gcd(f, t ^ x);
        if (g != 1u) return false;
    }
    return true;
}

u32 find_irreducible(int d) {
    if (d == 0) return 0;
    if (d == 1) return 0b11u;
    u32 start = (1u << d) | 1u; // monic with constant 1
    for (u32 f = start; ; f += 2u) { // step by 2 to keep constant term 1
        if (is_irreducible(f, d)) return f;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    long long n_ll;
    if (!(cin >> n_ll)) return 0;
    unsigned long long n = (unsigned long long)n_ll;

    if (n == 0) {
        cout << 0 << "\n\n";
        return 0;
    }

    // Number of bits K = floor(log2(n)) + 1
    int K = 64 - __builtin_clzll(n);
    if (K <= 1) {
        // n >= 1
        cout << 1 << "\n1\n";
        return 0;
    }

    int d = K / 2; // floor
    if (d == 0) {
        cout << 1 << "\n1\n";
        return 0;
    }

    u32 mod = find_irreducible(d);

    vector<u32> elems;
    elems.reserve(1u << d);

    // We'll use constant XOR C = 1 to avoid zero and improve coverage near boundaries.
    u32 C = 1u;

    for (u32 x = 0; x < (1u << d); ++x) {
        u32 x2 = gf_mul(x, x, mod, d);
        u32 x3 = gf_mul(x2, x, mod, d);
        u64 val = ((u64)x << d) | x3;
        val ^= C;
        if (val >= 1 && val <= n) elems.push_back((u32)val);
    }

    // Ensure distinctness and within [1, n] already satisfied by construction and filtering.
    cout << elems.size() << "\n";
    for (size_t i = 0; i < elems.size(); ++i) {
        if (i) cout << ' ';
        cout << elems[i];
    }
    cout << "\n";
    return 0;
}