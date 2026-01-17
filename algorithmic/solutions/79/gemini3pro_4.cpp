#include <iostream>
#include <vector>
#include <random>
#include <algorithm>

using namespace std;

// Use __int128 for modular arithmetic to prevent overflow with 60-bit n
typedef unsigned long long ull;
typedef unsigned __int128 u128;

// Function to calculate bits(x) as defined
// bits(x) = ceil(log2(x+1))
// This corresponds to the number of bits required to represent x, 
// or 0 if x is 0.
inline ull bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Cost function for multiplication modulo n as described in the problem
inline ull cost_mul(ull x, ull y) {
    return (bits(x) + 1) * (bits(y) + 1);
}

// Modular multiplication
inline ull mul(ull a, ull b, ull n) {
    return (ull)((u128)a * b % n);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ull n;
    if (!(cin >> n)) return 0;

    // Number of queries to perform.
    // We use a statistical attack (Correlation Power Analysis).
    // The variance of bits(a) is small but sufficient to detect the correlation
    // given enough samples. 6000 samples is well within the 30000 limit and provides robust statistics.
    const int NUM_QUERIES = 6000;
    
    vector<ull> inputs(NUM_QUERIES);
    vector<long long> residuals(NUM_QUERIES);
    
    // Random number generator
    mt19937_64 rng(1337);
    // Generate inputs in [2, n-1]. 0 and 1 are trivial and provide less information/variation.
    uniform_int_distribution<ull> dist(2, n - 1);

    // Perform queries and collect timing data
    for (int i = 0; i < NUM_QUERIES; ++i) {
        inputs[i] = dist(rng);
        cout << "? " << inputs[i] << endl;
        cin >> residuals[i];
    }

    // Precompute the sequence of 'a' values for each query through the 60 iterations.
    // a_seq[m][k] corresponds to the value of 'a' at the start of iteration k for query m.
    // Also subtract the deterministic base cost (all unconditional a*a multiplications) from the total time.
    vector<vector<ull>> a_seq(NUM_QUERIES, vector<ull>(60));
    
    for (int m = 0; m < NUM_QUERIES; ++m) {
        ull a = inputs[m];
        long long base_cost = 0;
        for (int k = 0; k < 60; ++k) {
            a_seq[m][k] = a;
            base_cost += cost_mul(a, a);
            a = mul(a, a, n);
        }
        residuals[m] -= base_cost;
    }

    ull d = 0;
    // r keeps track of the current value of 'r' in the modular exponentiation for each query
    vector<ull> r(NUM_QUERIES, 1);

    // Iteratively determine bits of d from LSB (bit 0) to MSB (bit 59)
    for (int k = 0; k < 60; ++k) {
        // We test the hypothesis for the k-th bit of d.
        // If d_k = 1, the residual time includes the term cost(r_k, a_k).
        // cost(r_k, a_k) = (bits(r_k)+1) * (bits(a_k)+1).
        // This term is linearly correlated with bits(a_k).
        // If d_k = 0, the residual time consists of future terms which depend on squarings of a_k.
        // Due to the scrambling nature of modular squaring, bits(a_k^2) is weakly correlated with bits(a_k).
        // Thus, we check for correlation between the residual time and bits(a_k).

        double sum_x = 0;
        double sum_y = 0;
        double sum_sq_x = 0;
        double sum_xy = 0;

        for (int m = 0; m < NUM_QUERIES; ++m) {
            double x = (double)(bits(a_seq[m][k]) + 1);
            double y = (double)residuals[m];
            
            sum_x += x;
            sum_y += y;
            sum_sq_x += x * x;
            sum_xy += x * y;
        }
        
        double mean_x = sum_x / NUM_QUERIES;
        double mean_y = sum_y / NUM_QUERIES;
        
        double cov = (sum_xy / NUM_QUERIES) - (mean_x * mean_y);
        double var_x = (sum_sq_x / NUM_QUERIES) - (mean_x * mean_x);
        
        // Calculate slope of the regression line Y = alpha + beta * X
        double slope = 0;
        if (var_x > 1e-9) {
            slope = cov / var_x;
        }
        
        // If d_k = 1, the expected slope is E[bits(r_k) + 1]. Since r_k is roughly uniform in [1, n-1],
        // this expectation is close to 60.
        // If d_k = 0, the expected slope is 0.
        // We use a threshold of 20 to safely distinguish.
        bool bit = (slope > 20.0);
        
        if (bit) {
            d |= (1ULL << k);
            // If the bit is 1, we must subtract the cost of this multiplication from the residuals
            // and update the state of r for the next iterations.
            for (int m = 0; m < NUM_QUERIES; ++m) {
                ull c = cost_mul(r[m], a_seq[m][k]);
                residuals[m] -= c;
                r[m] = mul(r[m], a_seq[m][k], n);
            }
        }
        // If bit is 0, r does not change, and there is no cost to subtract for this step.
    }

    cout << "! " << d << endl;

    return 0;
}