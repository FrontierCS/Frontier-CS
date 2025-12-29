#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;
typedef __int128_t int128;

// Miller-Rabin Primality Test
ll power(ll base, ll exp, ll mod) {
    ll res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (int128)res * base % mod;
        base = (int128)base * base % mod;
        exp /= 2;
    }
    return res;
}

bool check_composite(ll n, ll a, ll d, int s) {
    ll x = power(a, d, n);
    if (x == 1 || x == n - 1) return false;
    for (int r = 1; r < s; r++) {
        x = (int128)x * x % n;
        if (x == n - 1) return false;
    }
    return true;
}

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) {
        d /= 2;
        s++;
    }
    static const vector<ll> bases = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (ll a : bases) {
        if (n <= a) break;
        if (check_composite(n, a, d, s)) return false;
    }
    return true;
}

ll gcd_func(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Pollard's Rho Algorithm to find a non-trivial factor
ll pollard_rho(ll n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;
    ll x = 2, y = 2, d = 1, c = 1;
    auto f = [&](ll x) { return ((int128)x * x + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = gcd_func((x > y ? x - y : y - x), n);
        if (d == n) { // failure, retry with different c
            x = 2; y = 2; d = 1; c++;
        }
    }
    return d;
}

// Recursive function to construct the permutation
vector<int> solve(ll k) {
    if (k == 1) return {};
    
    // If even, divide by 2 (Prepend min element)
    // Corresponds to operation: P -> [0, P+1]
    if (k % 2 == 0) {
        vector<int> p = solve(k / 2);
        for (int &x : p) x++;
        p.insert(p.begin(), 0);
        return p;
    }
    
    // If odd and composite, factorize k = d * (k/d)
    // Corresponds to concatenation: P_d (small values) followed by P_{k/d} (large values)
    if (!is_prime(k)) {
        ll d = pollard_rho(k);
        vector<int> p1 = solve(d);
        vector<int> p2 = solve(k / d);
        
        int offset = p1.size();
        for (int x : p2) {
            p1.push_back(x + offset);
        }
        return p1;
    }
    
    // If prime, subtract 1 (Append min element)
    // Corresponds to operation: P -> [P+1, 0]
    vector<int> p = solve(k - 1);
    for (int &x : p) x++;
    p.push_back(0);
    return p;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int q;
    if (cin >> q) {
        vector<ll> ks(q);
        for (int i = 0; i < q; i++) cin >> ks[i];
        
        for (int i = 0; i < q; i++) {
            ll k = ks[i];
            vector<int> res = solve(k);
            cout << res.size() << "\n";
            for (size_t j = 0; j < res.size(); j++) {
                cout << res[j] << (j == res.size() - 1 ? "" : " ");
            }
            cout << "\n";
        }
    }
    return 0;
}