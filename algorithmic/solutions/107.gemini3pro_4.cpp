#include <iostream>
#include <vector>

using namespace std;

// Using long long for query values up to 10^18
typedef long long ll;
// Using __int128 for intermediate product overflow checks
typedef __int128_t int128;

// Function to perform a query: sends "0 Q" and reads gcd(X, Q)
ll query(ll q) {
    cout << "0 " << q << endl;
    ll g;
    cin >> g;
    return g;
}

void solve() {
    // 1. Identify all prime factors of X that are <= 1000.
    // X <= 10^9, so finding small factors allows us to isolate the "large" part.
    // Primes <= 1000 are precomputed/generated.
    vector<int> primes;
    vector<bool> is_prime(1001, true);
    for (int p = 2; p <= 1000; p++) {
        if (is_prime[p]) {
            primes.push_back(p);
            for (int i = 2 * p; i <= 1000; i += p)
                is_prime[i] = false;
        }
    }

    // We group primes into queries such that the product of primes in each query <= 10^18.
    // This allows us to check divisibility for many primes at once.
    vector<ll> queries;
    vector<vector<int>> query_primes;
    
    int128 curr = 1;
    vector<int> curr_primes;
    
    for (int p : primes) {
        // If adding this prime exceeds 10^18, save current batch and start new one
        if (curr * p > 1000000000000000000LL) {
            queries.push_back((ll)curr);
            query_primes.push_back(curr_primes);
            curr = 1;
            curr_primes.clear();
        }
        curr *= p;
        curr_primes.push_back(p);
    }
    // Don't forget the last batch
    if (curr > 1) {
        queries.push_back((ll)curr);
        query_primes.push_back(curr_primes);
    }

    // Execute detection queries and collect found prime factors
    vector<int> factors;
    for (size_t i = 0; i < queries.size(); i++) {
        ll g = query(queries[i]);
        for (int p : query_primes[i]) {
            if (g % p == 0) {
                factors.push_back(p);
            }
        }
    }

    // 2. Find exact exponents for the identified small prime factors.
    // For each factor p, we need to query p^k where p^k > X. Since X <= 10^9, p^k > 10^9 is enough.
    // gcd(X, p^k) will give p^{v_p(X)}.
    struct Check {
        int p;
        ll val;
    };
    vector<Check> checks;
    for (int p : factors) {
        ll val = p;
        while (val <= 1000000000LL) {
            val *= p;
        }
        checks.push_back({p, val});
    }

    ll divisor_count_small = 1;
    
    // Group exponent queries to minimize query count
    int idx = 0;
    while (idx < checks.size()) {
        curr = 1;
        vector<int> batch_ps;
        while (idx < checks.size()) {
            if (curr * checks[idx].val > 1000000000000000000LL) {
                break;
            }
            curr *= checks[idx].val;
            batch_ps.push_back(checks[idx].p);
            idx++;
        }
        
        // Execute the query for this batch of prime powers
        ll g = query((ll)curr);
        for (int p : batch_ps) {
            int count = 0;
            // Count how many times p divides the gcd result
            while (g % p == 0) {
                count++;
                g /= p;
            }
            divisor_count_small *= (count + 1);
        }
    }

    // 3. Estimate total divisors.
    // Let X = X_small * Y, where X_small contains all prime factors <= 1000.
    // Y has prime factors > 1000.
    // Since X <= 10^9 and min prime > 1000 is 1009, and 1009^3 > 10^9,
    // Y can have at most 2 prime factors (counted with multiplicity).
    // The possible values for d(Y) are {1, 2, 3, 4}.
    // We calculated divisor_count_small = d(X_small).
    // The true answer is divisor_count_small * d(Y).
    // We output 2 * divisor_count_small.
    // This satisfies the condition 1/2 <= ans / true_ans <= 2 for all d(Y) in {1,2,3,4}.
    cout << "1 " << divisor_count_small * 2 << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}