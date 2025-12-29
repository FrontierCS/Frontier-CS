#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

// Function to perform a query to the interactor
// Q: the number to query gcd with X
// Returns gcd(X, Q)
ll gcd_query(ll Q) {
    cout << "0 " << Q << endl;
    ll g;
    cin >> g;
    return g;
}

void solve() {
    // Strategy:
    // X <= 10^9. X^(1/3) = 1000.
    // If we find all prime factors of X up to 1000 and their exponents,
    // let the product of these prime powers be Y. Then X = Y * R.
    // The remaining part R has no prime factors <= 1000.
    // Since R * 1000^3 > R * (smallest prime in R)^3 (if R had 3 factors) >= X,
    // but X <= 10^9, R cannot have 3 or more prime factors (counting multiplicity).
    // Thus R has 0, 1, or 2 prime factors.
    // The number of divisors of R, denoted d(R), can be 1, 2, 3, or 4.
    // Let D be the number of divisors calculated from small factors (Y).
    // Then d(X) = D * d(R).
    // We output 2 * D.
    // This satisfies the condition 0.5 <= ans / true_val <= 2 for all d(R) in {1, 2, 3, 4}.
    
    // Step 1: Precompute primes up to 1000
    vector<int> primes;
    vector<bool> is_prime(1001, true);
    for (int p = 2; p <= 1000; p++) {
        if (is_prime[p]) {
            primes.push_back(p);
            for (int i = 2 * p; i <= 1000; i += p)
                is_prime[i] = false;
        }
    }

    // Step 2: Identify which primes <= 1000 are factors of X
    // We group primes into queries such that product <= 10^18.
    vector<int> factors;
    size_t idx = 0;
    while (idx < primes.size()) {
        ll Q = 1;
        vector<int> current_batch;
        // Pack as many primes as possible into Q
        while (idx < primes.size()) {
            ll p = primes[idx];
            // Check overflow against 10^18
            if (Q > 1000000000000000000LL / p) break;
            
            Q *= p;
            current_batch.push_back(p);
            idx++;
        }
        
        ll g = gcd_query(Q);
        
        // If gcd > 1, find which primes in the batch divide the gcd
        if (g > 1) {
            for (int p : current_batch) {
                if (g % p == 0) {
                    factors.push_back(p);
                }
            }
        }
    }

    // Step 3: Determine the exponent of each identified prime factor
    ll total_divisors_from_small = 1;
    size_t f_idx = 0;
    while (f_idx < factors.size()) {
        ll Q = 1;
        vector<pair<int, ll>> batch_powers; 
        // Pack powers of primes. We need p^k > 10^9 to ensure gcd(X, p^k) returns p^v_p(X)
        while (f_idx < factors.size()) {
            int p = factors[f_idx];
            ll pk = 1;
            while (pk <= 1000000000) pk *= p; // Ensure pk > 10^9
            
            if (Q > 1000000000000000000LL / pk) break;

            Q *= pk;
            batch_powers.push_back({p, pk});
            f_idx++;
        }
        
        ll g = gcd_query(Q);
        
        for (auto pair : batch_powers) {
            int p = pair.first;
            int count = 0;
            // Determine exponent of p in g
            while (g % p == 0) {
                count++;
                g /= p;
            }
            total_divisors_from_small *= (count + 1);
        }
    }

    // Output answer
    ll ans = total_divisors_from_small * 2;
    cout << "1 " << ans << endl;
}

int main() {
    // The problem is interactive. T is the number of games.
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}