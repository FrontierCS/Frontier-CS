#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

typedef long long ll;

// Helper to safely multiply and check bound
// Returns true if a * b <= limit
bool check_mul(ll a, ll b, ll limit) {
    if (a == 0 || b == 0) return true;
    return a <= limit / b;
}

vector<int> primes;

void precompute() {
    vector<bool> is_prime(1001, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p <= 1000; p++) {
        if (is_prime[p]) {
            primes.push_back(p);
            for (int i = 2 * p; i <= 1000; i += p)
                is_prime[i] = false;
        }
    }
}

void solve() {
    vector<int> found_primes;
    
    // Step 1: Identify prime factors <= 1000
    // We batch primes into queries such that product <= 10^18
    int p_idx = 0;
    while (p_idx < primes.size()) {
        ll Q = 1;
        vector<int> batch;
        // Greedily fill batch
        while (p_idx < primes.size()) {
            if (check_mul(Q, primes[p_idx], 1000000000000000000LL)) {
                Q *= primes[p_idx];
                batch.push_back(primes[p_idx]);
                p_idx++;
            } else {
                break;
            }
        }
        
        cout << "0 " << Q << endl;
        ll G;
        cin >> G;
        
        // If G > 1, some primes in this batch divide X
        if (G > 1) {
            for (int p : batch) {
                if (G % p == 0) {
                    found_primes.push_back(p);
                }
            }
        }
    }

    // Step 2: Find exponents for found primes
    ll ans_divisors = 1;
    
    struct Term {
        int p;
        ll val;
    };
    vector<Term> terms;
    for (int p : found_primes) {
        ll val = p;
        // We want val = p^k such that p^k <= 10^9 < p^(k+1)
        // Since X <= 10^9, the exponent of p in X cannot be greater than k.
        // Querying gcd(X, p^k) will give exactly p^(exponent in X).
        while (check_mul(val, p, 1000000000LL)) {
            val *= p;
        }
        terms.push_back({p, val});
    }

    int t_idx = 0;
    while (t_idx < terms.size()) {
        ll Q = 1;
        vector<Term> batch;
        while (t_idx < terms.size()) {
            if (check_mul(Q, terms[t_idx].val, 1000000000000000000LL)) {
                Q *= terms[t_idx].val;
                batch.push_back(terms[t_idx]);
                t_idx++;
            } else {
                break;
            }
        }

        cout << "0 " << Q << endl;
        ll G;
        cin >> G;

        for (auto& term : batch) {
            int count = 0;
            // Count exponent of term.p in G
            while (G % term.p == 0) {
                count++;
                G /= term.p;
            }
            ans_divisors *= (count + 1);
        }
    }

    // Step 3: Output answer
    // Let A be the part of X composed of primes <= 1000. We found d(A).
    // X = A * X_rem. Since X_rem has no prime factor <= 1000 and X <= 10^9,
    // X_rem can have at most 2 prime factors (since 1000^3 = 10^9).
    // Possible structures of X_rem: 1, p, p^2, p*q.
    // Corresponding number of divisors for X_rem: 1, 2, 3, 4.
    // Total d(X) = d(A) * d(X_rem).
    // Our guess is 2 * d(A).
    // The ratio ans / true_d will be:
    // If d(X_rem)=1 (true d = d(A)): 2/1 = 2.
    // If d(X_rem)=2 (true d = 2d(A)): 2/2 = 1.
    // If d(X_rem)=3 (true d = 3d(A)): 2/3 approx 0.67.
    // If d(X_rem)=4 (true d = 4d(A)): 2/4 = 0.5.
    // All ratios are within [0.5, 2].
    cout << "1 " << ans_divisors * 2 << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    precompute();
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}