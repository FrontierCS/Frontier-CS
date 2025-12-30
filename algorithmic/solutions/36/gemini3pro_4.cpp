#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <set>
#include <cstdlib>

using namespace std;

typedef long long ll;

ll total_cost = 0;

ll query(const vector<ll>& v) {
    if (v.empty()) return 0;
    if (v.size() == 1) return 0;
    
    total_cost += v.size();
    cout << "0 " << v.size();
    for (ll x : v) cout << " " << x;
    cout << endl;
    ll res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

set<ll> used_numbers;
mt19937_64 rng(12345);

vector<ll> generate_unique(int n) {
    vector<ll> res;
    res.reserve(n);
    while (res.size() < n) {
        ll x = uniform_int_distribution<ll>(1, 1000000000000000000LL)(rng);
        if (used_numbers.find(x) == used_numbers.end()) {
            used_numbers.insert(x);
            res.push_back(x);
        }
    }
    return res;
}

pair<ll, ll> find_crossing(vector<ll> L, vector<ll> R) {
    // Always split the larger set to balance recursion tree
    if (L.size() < R.size()) swap(L, R);
    
    if (L.size() == 1 && R.size() == 1) {
        return {L[0], R[0]};
    }
    
    int mid = L.size() / 2;
    vector<ll> L1(L.begin(), L.begin() + mid);
    vector<ll> L2(L.begin() + mid, L.end());
    
    // We want to check if there are collisions between L1 and R.
    // L1 and R are disjoint subsets of the original pool which had collisions.
    // The previous steps ensured that internal collisions of L and R are 0.
    // Therefore, internal collisions of L1 are 0.
    // query(L1 U R) returns exactly the number of crossing collisions.
    
    vector<ll> q = L1;
    q.insert(q.end(), R.begin(), R.end());
    
    if (query(q) > 0) {
        return find_crossing(L1, R);
    } else {
        return find_crossing(L2, R);
    }
}

pair<ll, ll> isolate(const vector<ll>& S) {
    if (S.size() < 2) return {0, 0};
    
    int mid = S.size() / 2;
    vector<ll> L(S.begin(), S.begin() + mid);
    vector<ll> R(S.begin() + mid, S.end());
    
    // Check internal collisions first.
    // This efficiently reduces problem size if collisions are within halves.
    if (query(L) > 0) return isolate(L);
    if (query(R) > 0) return isolate(R);
    
    // If no internal collisions in L or R, but S had collisions,
    // then the collision must be between an element in L and an element in R.
    return find_crossing(L, R);
}

ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ll ans = 0;
    vector<ll> pool;
    int sz = 100;
    int pairs_found = 0;

    // We target 4 pairs to ensure the GCD converges to n with high probability.
    // The budget is 1,000,000. We stop early if cost gets too high.
    while (pairs_found < 4 && total_cost < 800000) {
        int needed = sz - pool.size();
        if (needed > 0) {
            vector<ll> new_nums = generate_unique(needed);
            pool.insert(pool.end(), new_nums.begin(), new_nums.end());
        }
        
        ll c = query(pool);
        if (c == 0) {
            if (sz < 60000) sz *= 2;
            else sz += 10000;
            continue;
        }
        
        // Isolate a collision pair
        pair<ll, ll> p = isolate(pool);
        ll diff = abs(p.first - p.second);
        if (ans == 0) ans = diff;
        else ans = gcd(ans, diff);
        
        pairs_found++;
        
        // Remove one element of the pair from pool to find a new collision pair
        vector<ll> next_pool;
        next_pool.reserve(pool.size() - 1);
        for (ll x : pool) {
            if (x != p.first) next_pool.push_back(x);
        }
        pool = next_pool;
    }
    
    cout << "1 " << ans << endl;

    return 0;
}