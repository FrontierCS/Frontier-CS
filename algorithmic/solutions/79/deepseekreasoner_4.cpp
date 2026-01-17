#include <bits/stdc++.h>
using namespace std;
using ll = long long;
using ull = unsigned long long;
using i128 = __int128;

ll n; // global modulo

// -------- modular arithmetic with __int128 ----------
ll mulmod(ll a, ll b, ll m) {
    return (ll)((i128)a * b % m);
}

ll powmod(ll a, ll e, ll m) {
    ll res = 1;
    a %= m;
    while (e) {
        if (e & 1) res = mulmod(res, a, m);
        a = mulmod(a, a, m);
        e >>= 1;
    }
    return res;
}

// -------- bit length ----------
int bits(ll x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// -------- factoring (Pollard-Rho) ----------
ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

bool isPrime(ll n) {
    if (n < 2) return false;
    static const vector<ll> small_primes = {2,3,5,7,11,13,17,19,23,29,31,37};
    for (ll p : small_primes) {
        if (n % p == 0) return n == p;
    }
    // Miller–Rabin deterministic for 64-bit
    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) { d /= 2; ++s; }
    for (ll a : {2, 325, 9375, 28178, 450775, 9780504, 1795265022}) {
        if (a % n == 0) continue;
        ll x = powmod(a, d, n);
        if (x == 1 || x == n-1) continue;
        bool comp = true;
        for (int r = 0; r < s; ++r) {
            x = mulmod(x, x, n);
            if (x == n-1) { comp = false; break; }
        }
        if (comp) return false;
    }
    return true;
}

ll f(ll x, ll c, ll mod) {
    return (mulmod(x, x, mod) + c) % mod;
}

ll pollardRho(ll n) {
    if (n % 2 == 0) return 2;
    ll x = rand() % (n-2) + 2, y = x;
    ll c = rand() % (n-1) + 1;
    ll d = 1;
    while (d == 1) {
        x = f(x, c, n);
        y = f(y, c, n);
        y = f(y, c, n);
        d = gcd(abs(x - y), n);
    }
    return d;
}

void factor(ll n, vector<ll>& factors) {
    if (n == 1) return;
    if (isPrime(n)) {
        factors.push_back(n);
        return;
    }
    ll d = pollardRho(n);
    factor(d, factors);
    factor(n / d, factors);
}

// -------- time prediction for a given partial d ----------
// known: bits 0..k-1, dk is the assumed k-th bit, C = total popcount(d)
ll compute_time(ll a, const vector<int>& known, int dk, int C) {
    ll r = 1;
    ll total = 0;
    ll a_cur = a % n;
    int pop = 0;
    for (int b : known) if (b) ++pop;
    int k = known.size(); // current index k (we have known[0..k-1])
    
    // simulate steps i = 0 .. k-1
    for (int i = 0; i < k; ++i) {
        int ba = bits(a_cur);
        total += (ba + 1) * (ba + 1); // square
        if (known[i]) {
            int br = bits(r);
            total += (br