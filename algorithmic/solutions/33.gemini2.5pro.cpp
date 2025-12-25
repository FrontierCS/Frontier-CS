#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

using namespace std;

typedef long long ll;

int countSetBits(ll n) {
    if (n == 0) return 0;
    return __builtin_popcountll(n);
}

int get_msb_pos(ll n) {
    if (n == 0) return -1;
    return 63 - __builtin_clzll(n);
}

vector<int> generate_binary_perm(ll k) {
    if (k <= 1) {
        return {};
    }
    vector<int> p;
    int msb = get_msb_pos(k);
    for (int i = msb - 1; i >= 0; --i) {
        int current_len = p.size();
        vector<int> next_p(current_len + 1);
        next_p[0] = 0;
        for (int j = 0; j < current_len; ++j) {
            next_p[j + 1] = p[j] + 1;
        }
        p = next_p;

        if ((k >> i) & 1) {
            current_len = p.size();
            next_p.resize(current_len + 1);
            next_p[0] = current_len;
            for (int j = 0; j < current_len; ++j) {
                next_p[j + 1] = p[j];
            }
            p = next_p;
        }
    }
    return p;
}

int binary_len(ll k) {
    if (k <= 1) return 0;
    return get_msb_pos(k) + countSetBits(k) - 1;
}

map<ll, pair<int, vector<ll>>> memo;
vector<int> primes;

void sieve(int limit) {
    vector<bool> is_prime(limit + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= limit; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= limit; i += p)
                is_prime[i] = false;
        }
    }
    for (int p = 2; p <= limit; p++) {
        if (is_prime[p]) {
            primes.push_back(p);
        }
    }
}

pair<int, vector<ll>> find_best_factors(ll k) {
    if (k <= 1) {
        return {0, {}};
    }
    if (memo.count(k)) {
        return memo[k];
    }

    int best_len = binary_len(k);
    vector<ll> best_factors = {};

    for (int p : primes) {
        if ((ll)p * p > k && k > p ) continue; // Optimization
        if (k % p == 0) {
            auto res = find_best_factors(k / p);
            int current_len = (p - 1) + res.first;
            if (current_len < best_len) {
                best_len = current_len;
                best_factors = res.second;
                best_factors.push_back(p);
            }
        }
    }
    
    return memo[k] = {best_len, best_factors};
}

void solve() {
    ll k;
    cin >> k;
    
    auto res = find_best_factors(k);
    vector<ll> factors = res.second;
    ll rem = k;
    for(ll f : factors) {
        rem /= f;
    }

    vector<int> p;
    int current_val = 0;

    sort(factors.begin(), factors.end());
    for (ll f : factors) {
        int len = f - 1;
        for (int i = 0; i < len; ++i) {
            p.push_back(current_val + len - 1 - i);
        }
        current_val += len;
    }
    
    if (rem > 1) {
        vector<int> rem_p = generate_binary_perm(rem);
        for (int val : rem_p) {
            p.push_back(val + current_val);
        }
    }
    
    cout << p.size() << "\n";
    for (int i = 0; i < p.size(); ++i) {
        cout << p[i] << (i == (int)p.size() - 1 ? "" : " ");
    }
    cout << "\n";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    sieve(300);
    int q;
    cin >> q;
    while (q--) {
        memo.clear();
        solve();
    }
    return 0;
}