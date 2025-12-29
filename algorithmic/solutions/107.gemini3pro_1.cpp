#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

vector<int> primes;

// Sieve to find primes up to n
void sieve(int n) {
    vector<bool> is_prime(n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= n; p++) {
        if (is_prime[p]) {
            for (int i = p * p; i <= n; i += p)
                is_prime[i] = false;
        }
    }
    for (int p = 2; p <= n; p++) {
        if (is_prime[p]) {
            primes.push_back(p);
        }
    }
}

// Function to perform a query
ll query(ll q) {
    cout << "0 " << q << endl;
    ll g;
    cin >> g;
    return g;
}

void solve() {
    // Phase 1: Detect prime factors <= 1000
    // We group primes into batches such that their product <= 10^18.
    // Querying the product allows us to check divisibility for all primes in the batch.
    
    vector<int> present_primes;
    int idx = 0;
    while (idx < primes.size()) {
        ll q = 1;
        vector<int> batch;
        
        while (idx < primes.size()) {
            ll p = primes[idx];
            // Check if q * p <= 10^18
            if (1000000000000000000LL / p >= q) {
                q *= p;
                batch.push_back(p);
                idx++;
            } else {
                break;
            }
        }
        
        ll g = query(q);
        
        // If g > 1, find which primes from the batch divide g
        if (g > 1) {
            for (int p : batch) {
                if (g % p == 0) {
                    present_primes.push_back(p);
                }
            }
        }
    }
    
    // Phase 2: Find the exact exponent for each present prime
    // For each prime p found in Phase 1, we calculate k such that p^k > 10^9.
    // Querying with this power ensures we capture the full exponent of p in X.
    
    ll d_known = 1;
    int p_idx = 0;
    
    while (p_idx < present_primes.size()) {
        ll q = 1;
        vector<int> batch;
        
        while (p_idx < present_primes.size()) {
            int p = present_primes[p_idx];
            ll p_pow = p;
            // Calculate minimal power > 10^9
            while (p_pow <= 1000000000LL) {
                p_pow *= p;
            }
            
            // Try to add this power to the current query product
            if (1000000000000000000LL / p_pow >= q) {
                q *= p_pow;
                batch.push_back(p);
                p_idx++;
            } else {
                break;
            }
        }
        
        ll g = query(q);
        
        for (int p : batch) {
            int exponent = 0;
            // Determine exponent by repeated division
            while (g % p == 0) {
                exponent++;
                g /= p;
            }
            d_known *= (exponent + 1);
        }
    }
    
    // Calculate final answer.
    // X = X_known * Y. 
    // X_known consists of prime factors <= 1000, which we have fully determined.
    // Y consists of prime factors > 1000.
    // Since X <= 10^9 and factors of Y are > 1000, Y can have at most 2 prime factors.
    // Thus d(Y) can be 1, 2, 3, or 4.
    // The true number of divisors is d_known * d(Y).
    // Our guess is d_known * 2.
    // Relative error check: 0.5 <= (2 * d_known) / (d(Y) * d_known) <= 2
    // <=> 0.5 <= 2 / d(Y) <= 2.
    // This holds for d(Y) in {1, 2, 3, 4}.
    
    cout << "1 " << d_known * 2 << endl;
}

int main() {
    // Sieve primes up to 1000. 
    // We choose 1000 because 1000^3 = 10^9, so any number <= 10^9 has at most 2 prime factors > 1000.
    sieve(1000);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}