#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <set>
#include <map>
#include <chrono>
#include <cstdlib>

using namespace std;

typedef long long ll;

// Interaction helper
ll query(const vector<ll>& v) {
    if (v.empty()) return 0;
    cout << "0 " << v.size();
    for (ll x : v) {
        cout << " " << x;
    }
    cout << endl;
    ll collisions;
    cin >> collisions;
    return collisions;
}

void answer(ll n) {
    cout << "1 " << n << endl;
    exit(0);
}

// Math helpers
ll mul(ll a, ll b, ll m) {
    return (ll)((__int128)a * b % m);
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

    for (int i = 0; i < k; i++) {
        ll a = 2 + rand() % (n - 3);
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
        d = gcd((x > y ? x - y : y - x), n);
        if (d == n) { // failure, retry with different c
            x = rand() % (n-2) + 2;
            y = x;
            c = rand() % (n-1) + 1;
            d = 1;
        }
    }
    return d;
}

void factorize(ll n, map<ll, int>& factors) {
    if (n == 1) return;
    if (miller_rabin(n)) {
        factors[n]++;
        return;
    }
    ll d = pollard_rho(n);
    factorize(d, factors);
    factorize(n / d, factors);
}

void get_divisors(map<ll, int>::iterator it, map<ll, int>::iterator end, ll current, vector<ll>& divisors) {
    if (it == end) {
        divisors.push_back(current);
        return;
    }
    ll p = it->first;
    int count = it->second;
    ll p_pow = 1;
    for (int i = 0; i <= count; i++) {
        get_divisors(next(it), end, current * p_pow, divisors);
        if (i < count) p_pow *= p;
    }
}

// Logic to isolate a colliding pair
pair<ll, ll> find_cross(vector<ll> A, vector<ll> B) {
    if (A.size() == 1 && B.size() == 1) {
        return {A[0], B[0]};
    }

    if (A.size() > 1) {
        int mid = A.size() / 2;
        vector<ll> A1(A.begin(), A.begin() + mid);
        vector<ll> A2(A.begin() + mid, A.end());
        
        vector<ll> query_set = A1;
        query_set.insert(query_set.end(), B.begin(), B.end());
        
        ll c = query(query_set);
        if (c > 0) {
            return find_cross(A1, B);
        } else {
            return find_cross(A2, B);
        }
    } else {
        // |A| == 1, Split B
        int mid = B.size() / 2;
        vector<ll> B1(B.begin(), B.begin() + mid);
        vector<ll> B2(B.begin() + mid, B.end());
        
        vector<ll> query_set = A; // size 1
        query_set.insert(query_set.end(), B1.begin(), B1.end());
        
        ll c = query(query_set);
        if (c > 0) {
            return find_cross(A, B1);
        } else {
            return find_cross(A, B2);
        }
    }
}

pair<ll, ll> solve_set(vector<ll> S) {
    if (S.size() < 2) return {0, 0}; 
    
    int mid = S.size() / 2;
    vector<ll> S1(S.begin(), S.begin() + mid);
    vector<ll> S2(S.begin() + mid, S.end());
    
    ll c1 = query(S1);
    if (c1 > 0) return solve_set(S1);
    
    ll c2 = query(S2);
    if (c2 > 0) return solve_set(S2);
    
    return find_cross(S1, S2);
}

int main() {
    srand(time(0));
    
    // 1. Try small range detection
    int m_small = 500; 
    vector<ll> small_q;
    for(int i=1; i<=m_small; ++i) small_q.push_back(i);
    ll c_small = query(small_q);
    if (c_small > 0) {
        for (ll cand = 2; cand < m_small; ++cand) {
             vector<ll> test = {1, 1 + cand};
             if (query(test) > 0) {
                 answer(cand);
             }
        }
    }

    // 2. Large n: Birthday attack
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<ll> dist(1, 1000000000000000000LL);
    
    vector<ll> S;
    set<ll> distinct_S;
    
    ll k = 100;
    while (true) {
        while (S.size() < k) {
            ll x = dist(rng);
            while (distinct_S.count(x)) x = dist(rng);
            distinct_S.insert(x);
            S.push_back(x);
        }
        
        ll c = query(S);
        if (c > 0) break;
        
        k = (ll)(k * 1.5);
        if (k > 200000) k = 200000; // Limit
    }
    
    // 3. Isolate pair
    pair<ll, ll> p = solve_set(S);
    ll diff = abs(p.first - p.second);
    
    // 4. Factorize diff
    map<ll, int> factors;
    factorize(diff, factors);
    vector<ll> divisors;
    get_divisors(factors.begin(), factors.end(), 1, divisors);
    sort(divisors.begin(), divisors.end());
    
    // 5. Check divisors
    for (ll d : divisors) {
        if (d < 2) continue;
        if (d > 1000000000) break;
        
        vector<ll> test = {1, 1 + d};
        if (query(test) > 0) {
            answer(d);
        }
    }
    
    return 0;
}