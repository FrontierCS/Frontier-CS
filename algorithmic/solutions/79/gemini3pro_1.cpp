/**
 * Solution for Problem H. Hack
 * 
 * Approach:
 * The total execution time T(a) for a given input 'a' is:
 * T(a) = Sum_{i=0}^{59} [ Cost(a_i, a_i) + (d_i == 1 ? Cost(r_i, a_i) : 0) ]
 * where a_i = a^(2^i) mod n, and r_i is the accumulated result up to step i.
 * 
 * We can subtract the squaring costs Cost(a_i, a_i) from the measured time since they occur regardless of d.
 * Let Residual(a) be the remaining time.
 * We determine the bits of d from LSB (d_0) to MSB (d_59).
 * 
 * Suppose we have determined d_0, ..., d_{k-1}. We can compute r_k for any 'a'.
 * We want to determine d_k.
 * Residual(a) = d_k * Cost(r_k, a_k) + FutureTerms(a)
 * 
 * Cost(r_k, a_k) = (bits(r_k) + 1) * (bits(a_k) + 1).
 * 
 * If d_k = 1, Residual(a) contains a term proportional to bits(a_k).
 * If d_k = 0, Residual(a) consists of FutureTerms. The first term of FutureTerms depends on r_{k+1}.
 * If d_k = 0, r_{k+1} = r_k. The future costs depend on r_k but are effectively uncorrelated with bits(a_k) 
 * (because a_{k+1}, a_{k+2}... are derived from a_k by squaring modulo n, which decorrelates the bit counts for large n).
 * 
 * Thus, we can detect d_k = 1 by checking the correlation between Residual(a) and bits(a_k).
 * A significant positive covariance implies d_k = 1.
 * 
 * We use 10,000 queries to ensure statistical significance.
 */

#include <iostream>
#include <vector>
#include <random>
#include <cmath>
#include <numeric>

using namespace std;

typedef long long ll;
typedef unsigned long long ull;

// Calculate number of bits in x (without leading zeros)
// bits(0) = 0, bits(1) = 1, bits(2) = 2, etc.
int get_bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Modular multiplication: (a * b) % n
// Using __int128 to prevent overflow during multiplication
ull mul_mod(ull a, ull b, ull n) {
    return (ull)((unsigned __int128)a * b % n);
}

// Cost function as defined in the problem
// (bits(x) + 1) * (bits(y) + 1)
ll cost_func(ull x, ull y) {
    return (ll)(get_bits(x) + 1) * (get_bits(y) + 1);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ull n;
    if (!(cin >> n)) return 0;

    // Number of queries to perform. 
    // 30000 is the limit, 10000 is sufficient for high confidence.
    const int NUM_QUERIES = 10000;
    
    vector<ull> queries(NUM_QUERIES);
    vector<ll> times(NUM_QUERIES);
    
    // Random number generator
    mt19937_64 rng(1337); 
    uniform_int_distribution<ull> dist(2, n - 1); 

    // Step 1: Perform queries and collect computation times
    for (int i = 0; i < NUM_QUERIES; ++i) {
        ull a = dist(rng);
        queries[i] = a;
        cout << "? " << a << endl; // Flush after each request
        cin >> times[i];
    }

    // Precompute a_k values for all queries and all bit positions 0..59
    // a_k is the value of 'a' at the start of iteration k (i.e., a^(2^k) mod n)
    // Also, subtract the deterministic squaring costs from the measured times.
    vector<vector<ull>> a_vals(NUM_QUERIES, vector<ull>(60));
    
    for (int i = 0; i < NUM_QUERIES; ++i) {
        ull curr_a = queries[i];
        for (int k = 0; k < 60; ++k) {
            a_vals[i][k] = curr_a;
            // The algorithm always performs a = a * a % n at the end of the loop body
            // We subtract this cost immediately as it doesn't depend on d
            times[i] -= cost_func(curr_a, curr_a);
            curr_a = mul_mod(curr_a, curr_a, n);
        }
    }

    // Track the current value of 'r' for each query. Initially r = 1.
    vector<ull> r_vals(NUM_QUERIES, 1);
    
    // The secret exponent d
    ull d = 0;

    // Step 2: Determine bits of d from 0 to 59
    for (int k = 0; k < 60; ++k) {
        double mean_feat = 0;
        double mean_res = 0;
        
        // Feature: bits(a_k)
        vector<double> feats(NUM_QUERIES);
        
        for (int i = 0; i < NUM_QUERIES; ++i) {
            feats[i] = (double)get_bits(a_vals[i][k]);
            mean_feat += feats[i];
            mean_res += times[i];
        }
        mean_feat /= NUM_QUERIES;
        mean_res /= NUM_QUERIES;
        
        // Calculate covariance between Residual Time and bits(a_k)
        double cov = 0;
        for (int i = 0; i < NUM_QUERIES; ++i) {
            cov += (times[i] - mean_res) * (feats[i] - mean_feat);
        }
        
        // Calculate the Expected Covariance assuming d_k = 1
        // The term contributing to covariance is cost(r_k, a_k) = (bits(r_k)+1)*(bits(a_k)+1)
        double expected_cov = 0;
        for(int i = 0; i < NUM_QUERIES; ++i) {
             expected_cov += (double)(get_bits(r_vals[i]) + 1) * (feats[i] - mean_feat) * (feats[i] - mean_feat);
        }
        
        // If d_k = 1, measured covariance should be close to expected_cov.
        // If d_k = 0, measured covariance should be close to 0.
        // We use a threshold at 50% of the expected signal.
        if (cov > 0.5 * expected_cov) {
            d |= (1ULL << k);
            
            // If d_k = 1, we must update the residuals by removing the cost of the multiplication
            // and update the state of r for the next iterations.
            for (int i = 0; i < NUM_QUERIES; ++i) {
                times[i] -= cost_func(r_vals[i], a_vals[i][k]);
                r_vals[i] = mul_mod(r_vals[i], a_vals[i][k], n);
            }
        } else {
            // If d_k = 0, the multiplication didn't happen.
            // Residuals remain the same (minus future costs).
            // r remains the same.
        }
    }

    // Output the result
    cout << "! " << d << endl;

    return 0;
}