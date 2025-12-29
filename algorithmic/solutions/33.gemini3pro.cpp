#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

typedef long long ll;

// Fast modular multiplication for 64-bit integers
ll mult(ll a, ll b, ll mod) {
    return (ll)((__int128)a * b % mod);
}

// Modular exponentiation
ll power(ll base, ll exp, ll mod) {
    ll res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = mult(res, base, mod);
        base = mult(base, base, mod);
        exp /= 2;
    }
    return res;
}

// Miller-Rabin primality test
bool miller_rabin(ll n) {
    if (n < 4) return n == 2 || n == 3;
    if (n % 2 == 0) return false;

    ll d = n - 1;
    int s = 0;
    while (d % 2 == 0) {
        d /= 2;
        s++;
    }

    static const vector<ll> bases = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (ll a : bases) {
        if (n <= a) break;
        ll x = power(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; r++) {
            x = mult(x, x, n);
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
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Pollard's rho algorithm for factorization
ll pollard_rho(ll n) {
    if (n == 1) return 1;
    if (n % 2 == 0) return 2;
    ll x = 2, y = 2, d = 1, c = 1;
    auto f = [&](ll x) { return (mult(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = gcd(abs(x - y), n);
        if (d == n) { 
            // failure, retry with different c
            x = 2; y = 2; d = 1; c++;
        }
    }
    return d;
}

map<ll, int> memo_cost;
map<ll, pair<int, ll>> best_op; // 1: minus 1, 2: split factor

// Recursive function to find minimum permutation length
int solve(ll k) {
    if (k == 1) return 0;
    if (memo_cost.count(k)) return memo_cost[k];

    int res = 1e9;
    int type = -1;
    ll arg = -1;

    // Check factors
    if (k % 2 == 0) {
        // For even k, dividing by 2 is generally optimal
        int c = 1 + solve(k / 2);
        if (c < res) {
            res = c;
            type = 2;
            arg = 2;
        }
    } else {
        // Odd k
        // Option 1: Try finding a prime factor
        if (!miller_rabin(k)) {
            ll p = pollard_rho(k);
            // resolve fully to a prime factor
            while (!miller_rabin(p)) {
                p = pollard_rho(p);
            }
            // Cost is sum of parts
            int c_fact = solve(p) + solve(k / p);
            if (c_fact < res) {
                res = c_fact;
                type = 2;
                arg = p;
            }
        }
        
        // Option 2: Decrement by 1 (Append small)
        int c_minus = 1 + solve(k - 1);
        if (c_minus < res) {
            res = c_minus;
            type = 1;
            arg = -1;
        }
    }

    memo_cost[k] = res;
    best_op[k] = {type, arg};
    return res;
}

// Construct the permutation based on optimal moves
vector<int> construct(ll k) {
    if (k == 1) return {};
    solve(k); // Ensure computed
    auto op = best_op[k];
    
    if (op.first == 1) { // Minus 1
        vector<int> p = construct(k - 1);
        // Operation: Append an element smaller than all existing.
        // We shift existing elements up by 1 and append 0.
        for (auto &x : p) x++;
        p.push_back(0);
        return p;
    } else { // Factor d * (k/d)
        ll d = op.second;
        vector<int> p1 = construct(d);
        vector<int> p2 = construct(k / d);
        // Operation: Concatenate p1 and p2 such that all elements of p2 are larger than p1.
        // p1 values: 0 .. n1-1
        // p2 values: 0 .. n2-1
        // Shift p2 by n1.
        int n1 = p1.size();
        for (auto x : p2) {
            p1.push_back(x + n1);
        }
        return p1;
    }
}

void run_test_case() {
    int q;
    if (!(cin >> q)) return;
    vector<ll> ks(q);
    for(int i=0; i<q; ++i) cin >> ks[i];

    memo_cost[1] = 0;
    
    for (ll k : ks) {
        vector<int> res = construct(k);
        cout << res.size() << "\n";
        for (int i = 0; i < res.size(); ++i) {
            cout << res[i] << (i == res.size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    run_test_case();
    return 0;
}