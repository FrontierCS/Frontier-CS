#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

typedef long long ll;

// Memoization for cost and best move to reconstruct solution
map<ll, int> memo_cost;
map<ll, pair<int, ll>> best_move; // Type: 1=Mult(2^c), 2=Add(2^c-1), 3=Factor(d)

// Modular arithmetic helper functions
ll mul(ll a, ll b, ll m) {
    return (__int128)a * b % m;
}

ll power(ll a, ll b, ll m) {
    ll res = 1;
    a %= m;
    while (b > 0) {
        if (b & 1) res = mul(res, a, m);
        a = mul(a, a, m);
        b >>= 1;
    }
    return res;
}

// Miller-Rabin primality test
bool miller_rabin(ll n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0) return false;

    ll d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        s++;
    }

    static const ll bases[] = {2, 3, 5, 7, 11, 13, 17, 19, 23};
    for (int i = 0; i < 9; ++i) {
        ll a = bases[i];
        if (n <= a) break;
        ll x = power(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; ++r) {
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
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

// Pollard's Rho algorithm for factorization
ll pollard_rho(ll n) {
    if (n == 1) return 1;
    if (n % 2 == 0) return 2;
    ll x = 2, y = 2, d = 1, c = 1;
    auto f = [&](ll x) { return (mul(x, x, n) + c) % n; };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = gcd((x > y ? x - y : y - x), n);
        if (d == n) {
            x = rand() % (n - 2) + 2;
            y = x;
            c++;
            d = 1;
        }
    }
    return d;
}

// Calculate minimum permutation length to get exactly n increasing subsequences
int get_cost(ll n) {
    if (n == 1) return 0;
    if (memo_cost.count(n)) return memo_cost[n];

    int res = 1000000;
    pair<int, ll> move = {0, 0};

    // 1. Remove trailing zeros (equivalent to multiplication by 2^zeros)
    int zeros = 0;
    ll temp = n;
    while ((temp & 1) == 0) {
        temp >>= 1;
        zeros++;
    }
    if (zeros > 0) {
        int c = get_cost(temp) + zeros;
        if (c < res) {
            res = c;
            move = {1, zeros};
        }
    } else {
        // n is odd
        
        // 2. Try n-1 (equivalent to prepending max element)
        int c_sub1 = get_cost(n - 1) + 1;
        if (c_sub1 < res) {
            res = c_sub1;
            move = {2, 1};
        }

        // 3. Try removing a run of ones: n - (2^c - 1)
        int ones = 0;
        temp = n;
        while (temp & 1) {
            temp >>= 1;
            ones++;
        }
        if (ones > 1) {
            ll val = (1ULL << ones) - 1;
            if (n > val) {
                int c_run = get_cost(n - val) + ones;
                if (c_run < res) {
                    res = c_run;
                    move = {2, ones};
                }
            }
        }

        // 4. Try factorization
        if (!miller_rabin(n)) {
            ll d = pollard_rho(n);
            if (d != 1 && d != n) {
                int c_fact = get_cost(d) + get_cost(n / d);
                if (c_fact < res) {
                    res = c_fact;
                    move = {3, d};
                }
            }
        }
    }

    memo_cost[n] = res;
    best_move[n] = move;
    return res;
}

// Construct the permutation based on computed moves
vector<int> solve(ll n) {
    if (n == 1) return {};
    get_cost(n);
    pair<int, ll> m = best_move[n];
    
    vector<int> res;
    
    if (m.first == 1) { // Mult 2^c (append increasing seq of length c, values larger than current)
        int c = (int)m.second;
        res = solve(n >> c);
        int start = res.size();
        for (int i = 0; i < c; ++i) res.push_back(start + i);
    } 
    else if (m.first == 2) { // Add 2^c - 1 (prepend increasing seq of length c, values larger than current)
        int c = (int)m.second;
        ll val = (1ULL << c) - 1;
        res = solve(n - val);
        int current_size = res.size();
        vector<int> new_p;
        for (int i = 0; i < c; ++i) new_p.push_back(current_size + i);
        new_p.insert(new_p.end(), res.begin(), res.end());
        res = new_p;
    }
    else if (m.first == 3) { // Factor d (P_d concatenated with P_{n/d} shifted up)
        ll d = m.second;
        vector<int> p1 = solve(d);
        vector<int> p2 = solve(n / d);
        int offset = p1.size();
        for (int x : p2) p1.push_back(x + offset);
        res = p1;
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int q;
    if (cin >> q) {
        vector<ll> ks(q);
        for(int i=0; i<q; ++i) cin >> ks[i];
        for(int i=0; i<q; ++i) {
            memo_cost.clear();
            best_move.clear();
            vector<int> ans = solve(ks[i]);
            cout << ans.size() << "\n";
            for(int j=0; j<ans.size(); ++j) {
                cout << ans[j] << (j == (int)ans.size()-1 ? "" : " ");
            }
            cout << "\n";
        }
    }
    return 0;
}