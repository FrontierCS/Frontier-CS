#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <set>
#include <chrono>
#include <cstdlib>

using namespace std;

typedef long long ll;

// Sends a query to the interactor and returns the number of collisions
ll query(const vector<ll>& v) {
    if (v.empty()) return 0;
    cout << "0 " << v.size();
    for (size_t i = 0; i < v.size(); ++i) {
        cout << " " << v[i];
    }
    cout << endl;
    ll ans;
    cin >> ans;
    return ans;
}

// Sends the final guess to the interactor
void answer(ll n) {
    cout << "1 " << n << endl;
    exit(0);
}

// Calculates the expected collisions for a sequence 1, 2, ..., k inserted into n buckets
ll calculate_collisions_seq(ll n, ll k) {
    ll q = k / n;
    ll r = k % n;
    // r buckets have q+1 elements
    // n-r buckets have q elements
    ll term1 = r * (q * (q + 1) / 2);
    ll term2 = (n - r) * (q * (q - 1) / 2);
    return term1 + term2;
}

int main() {
    // Step 1: Check small n using a sequential query
    // A sequence 1..K will have predictable collision patterns based on n.
    // If n is small (<= 30000), we can detect it efficiently.
    ll small_k = 30000;
    vector<ll> small_q(small_k);
    iota(small_q.begin(), small_q.end(), 1);
    
    ll small_ans = query(small_q);
    
    if (small_ans > 0) {
        // Since the collision function is monotonic for relevant ranges, we can binary search.
        // For very small n, n divides k might cause slight steps, but it generally decreases.
        // Actually, for n <= k, f(n) is monotonically decreasing.
        ll low = 2, high = small_k;
        ll ans_n = -1;
        while (low <= high) {
            ll mid = low + (high - low) / 2;
            ll cols = calculate_collisions_seq(mid, small_k);
            if (cols == small_ans) {
                ans_n = mid;
                break; 
            } else if (cols < small_ans) {
                // If calculated collisions are fewer than observed, our n (guess) is too large.
                high = mid - 1;
            } else {
                // If calculated collisions are more than observed, our n (guess) is too small.
                low = mid + 1;
            }
        }
        
        if (ans_n != -1) {
            answer(ans_n);
        } else {
            // Fallback: linear scan if binary search fails due to local non-monotonicity (unlikely)
            for (ll n = 2; n <= small_k; ++n) {
                if (calculate_collisions_seq(n, small_k) == small_ans) {
                    answer(n);
                }
            }
        }
    }
    
    // Step 2: Large n. Use Randomized Birthday Attack.
    // We generate a set of random numbers. If n is large, collisions are rare.
    // With n up to 10^9, k=150000 gives k^2/(2n) approx 11 expected collisions.
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    ll large_k = 150000;
    
    while (true) {
        set<ll> s_set;
        // Generate distinct random numbers in range [1, 2e9]
        while (s_set.size() < large_k) {
            ll x = (rng() % 2000000000) + 1;
            s_set.insert(x);
        }
        vector<ll> s(s_set.begin(), s_set.end());
        
        ll current_collisions = query(s);
        if (current_collisions == 0) {
            // Unlikely case, or n > 2e9 (impossible per constraints). Retry.
            continue;
        }
        
        // Find a pair of elements (u, v) that collide (i.e., u = v mod n)
        // We use a divide and conquer approach, shrinking the set S.
        vector<ll> current_s = s;
        while (current_s.size() > 2) {
            // Shuffle to randomize the split
            shuffle(current_s.begin(), current_s.end(), rng);
            
            ll mid = current_s.size() / 2;
            vector<ll> left_part(current_s.begin(), current_s.begin() + mid);
            
            // Check if left half has internal collisions
            ll left_ans = query(left_part);
            if (left_ans > 0) {
                current_s = left_part;
                current_collisions = left_ans;
                continue;
            }
            
            // Check if right half has internal collisions
            vector<ll> right_part(current_s.begin() + mid, current_s.end());
            ll right_ans = query(right_part);
            if (right_ans > 0) {
                current_s = right_part;
                current_collisions = right_ans;
                continue;
            }
            
            // If neither has internal collisions, all collisions are between left and right.
            // In this case, we just restart the loop with a new shuffle to try and capture 
            // the collision inside one of the partitions.
        }
        
        // Now we have a pair {u, v} such that u = v mod n => |u - v| is a multiple of n.
        ll u = current_s[0];
        ll v = current_s[1];
        ll diff = abs(u - v);
        
        // n must be a divisor of diff.
        // We start with n_guess = diff and try to reduce it by removing prime factors.
        ll n_guess = diff;
        ll temp = diff;
        
        vector<ll> factors;
        for (ll i = 2; i * i <= temp; ++i) {
            while (temp % i == 0) {
                factors.push_back(i);
                temp /= i;
            }
        }
        if (temp > 1) factors.push_back(temp);
        
        // For each factor p, check if (n_guess / p) is still a multiple of n.
        // We check this by querying {1, 1 + n_guess/p}. If they collide, n divides n_guess/p.
        for (ll p : factors) {
            if (n_guess % p == 0) { 
                ll candidate = n_guess / p;
                vector<ll> probe = {1, 1 + candidate};
                if (query(probe) > 0) {
                    n_guess = candidate;
                }
            }
        }
        
        answer(n_guess);
    }
    
    return 0;
}