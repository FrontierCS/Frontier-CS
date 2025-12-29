#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cmath>
#include <numeric>

using namespace std;

typedef long long ll;

// For factorization
ll mul_mod(ll a, ll b, ll m) {
    return (__int128)a * b % m;
}

ll power(ll a, ll b, ll m) {
    ll res = 1;
    a %= m;
    while (b > 0) {
        if (b & 1) res = mul_mod(res, a, m);
        a = mul_mod(a, a, m);
        b >>= 1;
    }
    return res;
}

bool miller_rabin(ll n, int k=5) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;

    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) {
        d /= 2;
        s++;
    }

    // bases for n < 2^64
    static const vector<ll> bases = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (ll a : bases) {
        if (n <= a) break;
        ll x = power(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; r++) {
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

ll gcd(ll a, ll b) {
    return b == 0 ? a : gcd(b, a % b);
}

ll pollard_rho(ll n) {
    if (n == 1) return 1;
    if (n % 2 == 0) return 2;
    ll x = 2, y = 2, d = 1, c = 1;
    auto f = [&](ll x) { return (mul_mod(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = gcd(abs(x - y), n);
        if (d == n) { // failure, try different c
            x = 2; y = 2; d = 1; c++;
        }
    }
    return d;
}

ll get_prime_factor(ll n) {
    if (n % 2 == 0) return 2;
    if (miller_rabin(n)) return n;
    // Simple trial division for small factors
    for (ll i = 3; i * i <= 1000 && i < n; i += 2) {
        if (n % i == 0) return i;
    }
    return pollard_rho(n);
}

struct Solution {
    int cost;
    int type; // 1: sum_powers, 2: product, 3: sub1
    ll param; // m for type 1, divisor for type 2
};

map<ll, Solution> memo;

// Helper for sum_powers logic
int try_sum_powers(ll k, int m) {
    ll T = k + m - 1;
    if (T % 2 != 0) return 1e9;
    if (T < 2 * m) return 1e9;

    vector<int> bits;
    for (int i = 0; i < 62; i++) {
        if ((T >> i) & 1) bits.push_back(i);
    }
    
    if (bits.size() > m) return 1e9;

    int current_cost = 0;
    for (int x : bits) current_cost += x;
    
    int counts[65] = {0};
    for(int x : bits) counts[x]++;
    
    int needed = m - (int)bits.size();
    for (int i = 0; i < needed; i++) {
        int split_val = -1;
        for (int x = 2; x <= 62; x++) {
            if (counts[x] > 0) {
                split_val = x;
                break;
            }
        }
        if (split_val == -1) return 1e9; 
        counts[split_val]--;
        counts[split_val-1] += 2;
        current_cost += (split_val - 2);
    }
    
    return current_cost;
}

Solution solve(ll k) {
    if (k == 1) return {0, 0, 0};
    if (memo.count(k)) return memo[k];

    Solution best = {(int)1e9, 0, 0};

    // 1. Sum of Powers
    for (int m = 1; m <= 65; m++) {
        int c = try_sum_powers(k, m);
        if (c < best.cost) {
            best = {c, 1, (ll)m};
        }
    }

    // 2. Factorization
    ll p = get_prime_factor(k);
    if (p < k) {
        Solution s1 = solve(p);
        Solution s2 = solve(k / p);
        if (s1.cost + s2.cost < best.cost) {
            best = {s1.cost + s2.cost, 2, p};
        }
    } else {
        // Prime, try k-1
        Solution s = solve(k - 1);
        if (s.cost + 1 < best.cost) {
            best = {s.cost + 1, 3, 0};
        }
    }

    return memo[k] = best;
}

vector<int> construct(ll k) {
    if (k == 1) return {};
    Solution sol = solve(k);
    
    if (sol.type == 1) { // Sum of powers
        int m = (int)sol.param;
        ll T = k + m - 1;
        vector<int> exps;
        for (int i = 0; i < 62; i++) {
            if ((T >> i) & 1) exps.push_back(i);
        }
        int counts[65] = {0};
        for (int x : exps) counts[x]++;
        int needed = m - (int)exps.size();
        for (int i = 0; i < needed; i++) {
            for (int x = 2; x <= 62; x++) {
                if (counts[x] > 0) {
                    counts[x]--;
                    counts[x-1] += 2;
                    break;
                }
            }
        }
        vector<int> blocks;
        for (int x = 62; x >= 1; x--) {
            for (int i = 0; i < counts[x]; i++) blocks.push_back(x);
        }
        
        vector<int> res;
        int total_size = 0;
        for (int len : blocks) total_size += len;
        
        int start_val = total_size;
        for (int len : blocks) {
            start_val -= len;
            for (int i = 0; i < len; i++) {
                res.push_back(start_val + i);
            }
        }
        return res;
    } 
    else if (sol.type == 2) { // Product
        ll p = sol.param;
        vector<int> P = construct(p);
        vector<int> Q = construct(k / p);
        for (int &x : Q) x += P.size();
        P.insert(P.end(), Q.begin(), Q.end());
        return P;
    } 
    else { // k-1 + 1 (Append min)
        vector<int> P = construct(k - 1);
        for (int &x : P) x++;
        P.push_back(0);
        return P;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int q;
    if (!(cin >> q)) return 0;
    while (q--) {
        ll k;
        cin >> k;
        vector<int> res = construct(k);
        cout << res.size() << "\n";
        for (int i = 0; i < res.size(); i++) {
            cout << res[i] << (i == res.size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
    return 0;
}