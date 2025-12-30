#include <bits/stdc++.h>
using namespace std;
using ll = long long;
using ull = unsigned long long;
using i128 = __int128;

// ---------- Miller-Rabin and Pollard's Rho ----------
ll mod_mul(ll a, ll b, ll mod) {
    return (ll)((i128)a * b % mod);
}

ll mod_pow(ll a, ll e, ll mod) {
    ll res = 1;
    while (e) {
        if (e & 1) res = mod_mul(res, a, mod);
        a = mod_mul(a, a, mod);
        e >>= 1;
    }
    return res;
}

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;

    // deterministic for 64-bit: bases = {2, 325, 9375, 28178, 450775, 9780504, 1795265022}
    const vector<ll> bases = {2, 325, 9375, 28178, 450775, 9780504, 1795265022};
    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) d >>= 1, ++s;

    for (ll a : bases) {
        if (a % n == 0) continue;
        ll x = mod_pow(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool ok = false;
        for (int r = 0; r < s - 1; ++r) {
            x = mod_mul(x, x, n);
            if (x == n - 1) {
                ok = true;
                break;
            }
        }
        if (!ok) return false;
    }
    return true;
}

ll f(ll x, ll c, ll mod) {
    return (mod_mul(x, x, mod) + c) % mod;
}

ll pollard_rho(ll n) {
    if (n % 2 == 0) return 2;
    if (n % 3 == 0) return 3;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<ll> dist(1, n - 1);
    while (true) {
        ll c = dist(rng);
        ll x = dist(rng), y = x;
        ll d = 1;
        while (d == 1) {
            x = f(x, c, n);
            y = f(f(y, c, n), c, n);
            d = __gcd(abs(x - y), n);
        }
        if (d != n) return d;
    }
}

vector<ll> factorize(ll n) {
    if (n == 1) return {};
    if (is_prime(n)) return {n};
    ll d = pollard_rho(n);
    auto v1 = factorize(d);
    auto v2 = factorize(n / d);
    v1.insert(v1.end(), v2.begin(), v2.end());
    return v1;
}

// Generate all divisors from prime factors (with multiplicities)
void gen_divisors(const vector<pair<ll, int>>& factors, int idx, ll cur, vector<ll>& divisors) {
    if (idx == (int)factors.size()) {
        divisors.push_back(cur);
        return;
    }
    ll p = factors[idx].first;
    int e = factors[idx].second;
    ll mult = 1;
    for (int i = 0; i <= e; ++i) {
        gen_divisors(factors, idx + 1, cur * mult, divisors);
        mult *= p;
    }
}

vector<ll> get_divisors(ll n) {
    vector<ll> primes = factorize(n);
    sort(primes.begin(), primes.end());
    vector<pair<ll, int>> factors;
    for (ll p : primes) {
        if (factors.empty() || factors.back().first != p)
            factors.emplace_back(p, 1);
        else
            factors.back().second++;
    }
    vector<ll> divisors;
    gen_divisors(factors, 0, 1, divisors);
    sort(divisors.begin(), divisors.end());
    return divisors;
}

// ---------- Interactive Part ----------
mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

ll query(const vector<ll>& vals) {
    cout << "0 " << vals.size();
    for (ll x : vals) cout << " " << x;
    cout << endl;
    cout.flush();
    ll res;
    cin >> res;
    return res;
}

// S is the global set (original order)
vector<ll> S;

// Query a subset given indices (preserving order)
ll query_indices(const vector<int>& idx) {
    vector<ll> vals;
    for (int i : idx) vals.push_back(S[i]);
    return query(vals);
}

pair<ll, ll> find_cross_collision(const vector<int>& left, const vector<int>& right);

pair<ll, ll> find_collision(const vector<int>& idx) {
    if (idx.size() == 2) {
        return {S[idx[0]], S[idx[1]]};
    }
    int mid = idx.size() / 2;
    vector<int> left(idx.begin(), idx.begin() + mid);
    vector<int> right(idx.begin() + mid, idx.end());
    ll c_left = query_indices(left);
    if (c_left > 0) return find_collision(left);
    ll c_right = query_indices(right);
    if (c_right > 0) return find_collision(right);
    return find_cross_collision(left, right);
}

pair<ll, ll> find_cross_collision(const vector<int>& left, const vector<int>& right) {
    if (left.size() == 1 && right.size() == 1) {
        return {S[left[0]], S[right[0]]};
    }
    if (left.size() == 1) {
        int mid = right.size() / 2;
        vector<int> right1(right.begin(), right.begin() + mid);
        vector<int> right2(right.begin() + mid, right.end());
        // query left + right1
        vector<ll> q = {S[left[0]]};
        for (int i : right1) q.push_back(S[i]);
        if (query(q) > 0) {
            return find_cross_collision(left, right1);
        } else {
            return find_cross_collision(left, right2);
        }
    } else {
        int mid = left.size() / 2;
        vector<int> left1(left.begin(), left.begin() + mid);
        vector<int> left2(left.begin() + mid, left.end());
        // query left1 + right
        vector<ll> q;
        for (int i : left1) q.push_back(S[i]);
        for (int i : right) q.push_back(S[i]);
        if (query(q) > 0) {
            return find_cross_collision(left1, right);
        } else {
            return