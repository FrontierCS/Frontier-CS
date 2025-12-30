#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <random>
#include <chrono>

using namespace std;

typedef long long ll;

// Helper to interact with the judge
ll query(const vector<ll>& v) {
    if (v.empty()) return 0;
    cout << "0 " << v.size();
    for (ll x : v) cout << " " << x;
    cout << endl;
    ll res;
    cin >> res;
    if (res < 0) exit(0); // Should not happen based on problem description
    return res;
}

// Helper to output answer
void answer(ll n) {
    cout << "1 " << n << endl;
    exit(0);
}

// Local simulation of collision counting
ll count_collisions(const vector<ll>& v, ll n) {
    if (v.empty()) return 0;
    vector<ll> mods;
    mods.reserve(v.size());
    for (ll x : v) mods.push_back(x % n);
    sort(mods.begin(), mods.end());
    ll collisions = 0;
    ll current_streak = 0;
    for (size_t i = 0; i < mods.size(); ++i) {
        if (i > 0 && mods[i] == mods[i-1]) {
            current_streak++;
        } else {
            collisions += (current_streak * (current_streak + 1)) / 2;
            current_streak = 0;
        }
    }
    collisions += (current_streak * (current_streak + 1)) / 2;
    return collisions;
}

// Recursive function to isolate a colliding pair
pair<ll, ll> solve_pair(vector<ll> v) {
    // Base case for small size: perform robust cross-check
    // We use 60 as a threshold where O(N^2) or O(N) checks are cheap enough
    if (v.size() <= 60) { 
        size_t mid = v.size() / 2;
        vector<ll> s1(v.begin(), v.begin() + mid);
        vector<ll> s2(v.begin() + mid, v.end());
        
        // Check internal collisions first
        if (s1.size() > 1) {
             ll c1 = query(s1);
             if (c1 > 0) return solve_pair(s1);
        }
        if (s2.size() > 1) {
             ll c2 = query(s2);
             if (c2 > 0) return solve_pair(s2);
        }
        
        // If no internal collisions, must be cross collision
        // Search for u in s1 that collides with something in s2
        for (ll u : s1) {
            // Optimisation: check if u collides with ANY element in s2
            vector<ll> group = s2;
            group.push_back(u);
            // We know s2 has 0 internal collisions. 
            // So any collision in 'group' must involve u.
            if (query(group) > 0) {
                 // u collides with something in s2. Find it.
                 for (ll target : s2) {
                     vector<ll> pair_q = {u, target};
                     if (query(pair_q) > 0) return {u, target};
                 }
            }
        }
        return {0, 0};
    }
    
    // Large size: heuristic, recursive split without cross-check
    // If we are unlucky and only have cross-collisions, we fail and the main loop retries.
    size_t mid = v.size() / 2;
    vector<ll> s1(v.begin(), v.begin() + mid);
    vector<ll> s2(v.begin() + mid, v.end());
    
    ll c1 = query(s1);
    if (c1 > 0) return solve_pair(s1);
    
    ll c2 = query(s2);
    if (c2 > 0) return solve_pair(s2);
    
    return {0, 0};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    ll K = 100;
    // Use range up to 2*10^9. If n <= 10^9, differences will be small multiples of n.
    ll max_val = 2000000000LL; 
    
    while (true) {
        vector<ll> v;
        set<ll> used;
        // Generate random unique numbers
        while (v.size() < K) {
            ll x = (rng() % max_val) + 1;
            if (used.find(x) == used.end()) {
                used.insert(x);
                v.push_back(x);
            }
        }
        
        ll c = query(v);
        if (c == 0) {
            // No collisions, need more samples
            K *= 2;
            if (K > 45000) K = 45000; 
            continue;
        }
        
        // Collisions found. Try to extract a single pair (a, b) such that a = b mod n.
        pair<ll, ll> p = solve_pair(v);
        
        if (p.first != 0) {
            ll diff = abs(p.first - p.second);
            // n must be a divisor of diff.
            // Find all divisors of diff in range [2, 10^9]
            vector<ll> candidates;
            for (ll i = 1; i * i <= diff; ++i) {
                if (diff % i == 0) {
                    if (i >= 2 && i <= 1000000000LL) candidates.push_back(i);
                    ll j = diff / i;
                    if (j != i && j >= 2 && j <= 1000000000LL) candidates.push_back(j);
                }
            }
            
            // Filter candidates by checking if they produce exactly 'c' collisions on the original set 'v'
            vector<ll> next_candidates;
            for (ll cand : candidates) {
                if (count_collisions(v, cand) == c) {
                    next_candidates.push_back(cand);
                }
            }
            candidates = next_candidates;
            
            // If still ambiguous, use new random sets to filter
            while (candidates.size() > 1) {
                vector<ll> ver;
                used.clear();
                while (ver.size() < 100) {
                    ll x = (rng() % max_val) + 1;
                    if (used.find(x) == used.end()) {
                        used.insert(x);
                        ver.push_back(x);
                    }
                }
                ll ver_c = query(ver);
                next_candidates.clear();
                for (ll cand : candidates) {
                    if (count_collisions(ver, cand) == ver_c) {
                        next_candidates.push_back(cand);
                    }
                }
                candidates = next_candidates;
            }
            
            if (!candidates.empty()) {
                answer(candidates[0]);
            }
        }
        // If solve_pair failed (likely due to cross-collision in large set), 
        // we just loop again with a fresh random set.
    }

    return 0;
}