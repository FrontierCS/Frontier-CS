#include <iostream>
#include <vector>
#include <unordered_map>
#include <cstdint>
#include <algorithm>
#include <cmath>

using namespace std;

using ll = long long;

// Miller-Rabin primality test for 64-bit integers
ll mul_mod(ll a, ll b, ll mod) {
    return (__int128)a * b % mod;
}

ll pow_mod(ll a, ll d, ll mod) {
    ll res = 1;
    while (d) {
        if (d & 1) res = mul_mod(res, a, mod);
        a = mul_mod(a, a, mod);
        d >>= 1;
    }
    return res;
}

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2) return true;
    if (n % 2 == 0) return false;
    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) {
        d /= 2;
        ++s;
    }
    // Deterministic bases for 64-bit integers
    for (ll a : {2, 325, 9375, 28178, 450775, 9780504, 1795265022}) {
        if (a % n == 0) continue;
        ll x = pow_mod(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; ++r) {
            x = mul_mod(x, x, n);
            if (x == n - 1) {
                composite = false;
                break;
            }
        }
        if (composite) return false;
    }
    return true;
}

// Find a small divisor (up to 1e6) or return -1
ll find_divisor(ll n) {
    if (n % 2 == 0) return 2;
    for (ll d = 3; d <= 1000000; d += 2) {
        if (d * d > n) break;
        if (n % d == 0) return d;
    }
    return -1;
}

unordered_map<ll, pair<vector<int>, int>> memo;

pair<vector<int>, int> get_perm(ll k) {
    if (k == 2) {
        return { {0}, 1 };
    }
    auto it = memo.find(k);
    if (it != memo.end()) return it->second;

    bool prime = is_prime(k);
    // Try multiplicative decomposition if composite and a small divisor exists
    if (!prime) {
        ll d = find_divisor(k);
        if (d != -1) {
            ll a = d, b = k / d;
            auto [permA, lenA] = get_perm(a);
            auto [permB, lenB] = get_perm(b);
            vector<int> perm = permA;
            perm.reserve(lenA + lenB);
            for (int x : permB) perm.push_back(x + lenA);
            return memo[k] = {perm, lenA + lenB};
        }
    }

    // Additive decomposition: try b from 2 to 30
    const int B_MAX = 30;
    ll best_len = 1e18;
    vector<int> best_perm;
    for (int b = 2; b <= B_MAX; ++b) {
        if (k - b + 1 < 2) break;
        ll a = k - b + 1;
        auto [permA, lenA] = get_perm(a);
        auto [permB, lenB] = get_perm(b);
        ll total_len = lenA + lenB;
        if (total_len < best_len) {
            best_len = total_len;
            // construct additive permutation: first block (a) larger than second block (b)
            vector<int> perm;
            perm.reserve(total_len);
            for (int x : permA) perm.push_back(x + lenB);
            for (int x : permB) perm.push_back(x);
            best_perm = std::move(perm);
        }
    }

    return memo[k] = {best_perm, (int)best_len};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    cin >> q;
    vector<ll> ks(q);
    for (int i = 0; i < q; ++i) {
        cin >> ks[i];
    }

    for (ll k : ks) {
        auto [perm, n] = get_perm(k);
        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            cout << perm[i];
            if (i < n - 1) cout << " ";
        }
        cout << "\n";
    }

    return 0;
}