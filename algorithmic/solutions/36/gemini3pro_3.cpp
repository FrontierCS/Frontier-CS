#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <random>
#include <chrono>

using namespace std;

typedef long long ll;

// Interact with the judge
// Output: 0 m x1 x2 ... xm
// Input: number of collisions
ll query(const vector<ll>& v) {
    if (v.empty()) return 0;
    cout << "0 " << v.size();
    for (ll x : v) {
        cout << " " << x;
    }
    cout << endl;
    ll response;
    cin >> response;
    if (response == -1) exit(0); 
    return response;
}

// Report the answer
// Output: 1 n
void answer(ll n) {
    cout << "1 " << n << endl;
    exit(0);
}

// Global random engine
mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

// Recursive function to find a colliding pair in a set known to have collisions
// Invariant: s contains at least one pair colliding modulo n
pair<ll, ll> find_collision(vector<ll> s) {
    // Base case: Pair found
    if (s.size() == 2) {
        return {s[0], s[1]};
    }

    // Divide the set into two halves
    ll mid = s.size() / 2;
    vector<ll> left_part(s.begin(), s.begin() + mid);
    vector<ll> right_part(s.begin() + mid, s.end());

    // Check if collision is inside left part
    ll c_left = query(left_part);
    if (c_left > 0) {
        return find_collision(left_part);
    }

    // Check if collision is inside right part
    ll c_right = query(right_part);
    if (c_right > 0) {
        return find_collision(right_part);
    }

    // If no internal collisions in left or right, the collision must be between them
    // We assume s had collisions, and since neither half does, it's a cross collision.
    vector<ll> A = left_part;
    vector<ll> B = right_part;
    
    // Narrow down A and B until we have 1 element in each
    while (A.size() > 1 || B.size() > 1) {
        // Optimization: always split the larger set to minimize query size
        if (A.size() > B.size()) {
            ll midA = A.size() / 2;
            vector<ll> A1(A.begin(), A.begin() + midA);
            vector<ll> A2(A.begin() + midA, A.end());
            
            // Query A1 + B. Since A and B are internally collision-free,
            // any collision here must be between A1 and B.
            vector<ll> q = A1;
            q.insert(q.end(), B.begin(), B.end());
            
            if (query(q) > 0) {
                A = A1; 
            } else {
                A = A2; 
            }
        } else {
            ll midB = B.size() / 2;
            vector<ll> B1(B.begin(), B.begin() + midB);
            vector<ll> B2(B.begin() + midB, B.end());
            
            vector<ll> q = A;
            q.insert(q.end(), B1.begin(), B1.end());
            
            if (query(q) > 0) {
                B = B1;
            } else {
                B = B2;
            }
        }
    }
    return {A[0], B[0]};
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // K is the number of elements in each random query.
    // Based on Birthday Paradox, K approx sqrt(n) gives high collision probability.
    // For n = 10^9, K = 22000 gives acceptable probability (~20%) per try, 
    // and keeps the cost low enough to fit within 1,000,000 total cost after multiple tries and resolution.
    ll K = 22000;

    while (true) {
        set<ll> distinct_nums;
        while ((ll)distinct_nums.size() < K) {
            // Generate distinct random numbers.
            // Range 1 to 2*10^9 covers typical n=10^9 cases well.
            ll x = std::uniform_int_distribution<ll>(1, 2000000000LL)(rng);
            distinct_nums.insert(x);
        }
        vector<ll> q_vec(distinct_nums.begin(), distinct_nums.end());
        
        ll coll = query(q_vec);
        if (coll > 0) {
            // Collision detected, isolate the pair
            pair<ll, ll> p = find_collision(q_vec);
            ll diff = abs(p.first - p.second);
            
            // n must be a divisor of |u - v|
            vector<ll> divisors;
            for (ll i = 1; i * i <= diff; ++i) {
                if (diff % i == 0) {
                    divisors.push_back(i);
                    if (i * i != diff) {
                        divisors.push_back(diff / i);
                    }
                }
            }
            sort(divisors.begin(), divisors.end());
            
            // Find the smallest divisor d such that d is a multiple of n.
            // Since n is a divisor of diff, the smallest such divisor is n itself.
            // We check this by querying {1, 1+d}. If it collides, d is a multiple of n.
            for (ll d : divisors) {
                if (d < 2) continue; // n >= 2
                if (query({1, 1 + d}) > 0) {
                    answer(d);
                }
            }
            break;
        }
    }

    return 0;
}