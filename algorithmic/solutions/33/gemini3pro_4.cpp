#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <cmath>

using namespace std;

typedef long long ll;
typedef __int128_t int128;

ll mul(ll a, ll b, ll m) {
    return (ll)((int128)a * b % m);
}

ll power(ll a, ll b, ll m) {
    ll res = 1;
    a %= m;
    while (b > 0) {
        if (b % 2 == 1) res = mul(res, a, m);
        a = mul(a, a, m);
        b /= 2;
    }
    return res;
}

bool is_prime(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
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
            x = mul(x, x, n);
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
    auto f = [&](ll x) { return (mul(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = gcd(abs(x - y), n);
        if (d == n) { 
            x = 2; y = 2; d = 1; c++;
        }
    }
    return d;
}

map<ll, int> memo_cost;
map<ll, pair<int, ll>> strategy; 

int solve_cost(ll k) {
    if (k == 1) return 0;
    if (memo_cost.count(k)) return memo_cost[k];

    int res = 2000000000;
    int type = -1;
    ll param = -1;

    // Option 1: Divide by 2
    if (k % 2 == 0) {
        int c = solve_cost(k / 2);
        if (c + 1 < res) {
            res = c + 1;
            type = 1;
            param = 0;
        }
        memo_cost[k] = res;
        strategy[k] = {type, param};
        return res;
    }

    // Option 2: Factor
    if (!is_prime(k)) {
        ll d = pollard_rho(k);
        if (d != 1 && d != k) {
            int c1 = solve_cost(d);
            int c2 = solve_cost(k / d);
            if (c1 + c2 < res) {
                res = c1 + c2;
                type = 2;
                param = d;
            }
        }
    }

    // Option 3: Subtract 2^t - 1
    int logk = 0;
    {
        ll temp = k;
        while (temp >>= 1) logk++;
    }
    
    int trials = 0;
    // Always try t=1
    vector<int> ts;
    for (int t = logk; t >= 2; --t) ts.push_back(t);
    ts.push_back(1);

    for (int t : ts) {
        ll sub = (1LL << t) - 1;
        if (sub >= k) continue; 
        
        ll next_k = k - sub + 1; 
        
        // Pruning heuristic
        if (t + 1 >= res) continue; 

        int c = solve_cost(next_k);
        if (c + t < res) {
            res = c + t;
            type = 3;
            param = t;
        }
        
        if (t > 1) {
            trials++;
            if (trials > 4) { // Only check a few large t, but always check t=1 later
                // skip intermediate t
                if (ts.back() == 1 && t != 1) {
                    t = 2; // Jump to end (loop decrements will handle)
                }
            }
        }
    }

    memo_cost[k] = res;
    strategy[k] = {type, param};
    return res;
}

vector<ll> construct(ll k) {
    if (k == 1) return {};
    pair<int, ll> s = strategy[k];
    int type = s.first;
    ll param = s.second;

    if (type == 1) { 
        vector<ll> p = construct(k / 2);
        ll n = p.size();
        p.push_back(n);
        return p;
    } else if (type == 2) { 
        ll a = param;
        ll b = k / a;
        vector<ll> pa = construct(a);
        vector<ll> pb = construct(b);
        ll offset = pa.size();
        for (ll &x : pb) x += offset;
        pa.insert(pa.end(), pb.begin(), pb.end());
        return pa;
    } else { 
        int t = (int)param;
        ll next_k = k - ((1LL << t) - 1) + 1;
        vector<ll> prem = construct(next_k);
        for (ll &x : prem) x += t;
        vector<ll> res;
        for (ll x : prem) res.push_back(x);
        for (int i = 0; i < t; ++i) res.push_back(i);
        return res;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int q;
    if (!(cin >> q)) return 0;
    vector<ll> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int i = 0; i < q; ++i) {
        ll k = ks[i];
        solve_cost(k);
        vector<ll> res = construct(k);
        cout << res.size() << "\n";
        for (int j = 0; j < res.size(); ++j) {
            cout << res[j] << (j == res.size() - 1 ? "" : " ");
        }
        cout << "\n";
    }
    return 0;
}