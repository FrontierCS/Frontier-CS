#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

// Function to perform a query
ll query(ll q) {
    cout << "0 " << q << endl;
    ll g;
    cin >> g;
    return g;
}

void solve() {
    // Sieve primes up to 1000
    // Primes up to 1000 are sufficient because if X <= 10^9 has prime factors > 1000,
    // it can have at most 2 such factors (since 1000^3 = 10^9).
    vector<int> primes;
    vector<bool> is_prime(1001, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p <= 1000; p++) {
        if (is_prime[p]) {
            primes.push_back(p);
            for (int i = 2 * p; i <= 1000; i += p)
                is_prime[i] = false;
        }
    }
    
    // Precompute query batches
    // We group primes such that their product is <= 10^18
    vector<ll> batch_queries;
    vector<vector<int>> batch_primes;
    
    ll current_q = 1;
    vector<int> current_p;
    
    for (int p : primes) {
        // Check if current_q * p > 10^18 safely
        if (1000000000000000000ULL / p < (unsigned long long)current_q) {
            batch_queries.push_back(current_q);
            batch_primes.push_back(current_p);
            current_q = 1;
            current_p.clear();
        }
        current_q *= p;
        current_p.push_back(p);
    }
    if (current_q > 1) {
        batch_queries.push_back(current_q);
        batch_primes.push_back(current_p);
    }
    
    int T;
    if (!(cin >> T)) return;
    
    while (T--) {
        ll ans_d = 1;
        // Process each batch to find small prime factors
        for (size_t i = 0; i < batch_queries.size(); ++i) {
            ll q = batch_queries[i];
            ll g = query(q);
            
            if (g > 1) {
                // If the gcd > 1, some primes in this batch divide X
                for (int p : batch_primes[i]) {
                    if (g % p == 0) {
                        // Found a prime factor p.
                        // We need to find the exact exponent of p in X.
                        // We query the largest power of p <= 10^18.
                        // Since p >= 2, p^60 > 10^18, and X <= 10^9, 
                        // the largest power <= 10^18 will definitely cover the exponent in X.
                        ll p_pow = p;
                        while (p_pow <= 1000000000000000000ULL / p) {
                            p_pow *= p;
                        }
                        
                        ll gp = query(p_pow);
                        
                        int count = 0;
                        while (gp % p == 0) {
                            count++;
                            gp /= p;
                        }
                        ans_d *= (count + 1);
                    }
                }
            }
        }
        
        // After finding all prime factors <= 1000, the remaining part of X (let's call it X')
        // has only prime factors > 1000. Since X <= 10^9 and 1000^3 = 10^9,
        // X' can be 1, p, p^2, or pq.
        // The number of divisors of X' is thus 1, 2, 3, or 4.
        // We multiply our found divisor count by 2.
        // This guess works because 2 is within [0.5, 2] times the true value for any of {1, 2, 3, 4}.
        cout << "1 " << ans_d * 2 << endl;
    }
}

int main() {
    // Standard I/O setup
    solve();
    return 0;
}