#include <iostream>
#include <vector>
#include <random>
#include <algorithm>

using namespace std;

typedef unsigned long long ull;
typedef __int128_t int128;

// Function to calculate bits(x) = ceil(log2(x+1))
// Equivalent to finding the number of bits required to represent x
// bits(0)=0, bits(1)=1, bits(2)=2, etc.
int get_bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Cost function for multiplication modulo n
ull mult_cost(ull x, ull y) {
    return (ull)(get_bits(x) + 1) * (get_bits(y) + 1);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ull n;
    if (!(cin >> n)) return 0;

    // Use a sufficient number of queries to statistically distinguish the bit
    // 30000 total queries allowed. We use 15000 to be safe and accurate.
    int num_queries = 15000;
    vector<ull> A(num_queries);
    vector<long long> Times(num_queries);
    vector<ull> V(num_queries); // Stores current v_k(a) = a^(2^k) % n
    vector<ull> R(num_queries, 1); // Stores current R(a)

    // Random number generator
    mt19937_64 rng(1337);
    uniform_int_distribution<ull> dist(0, n - 1);

    // Perform queries
    for (int i = 0; i < num_queries; ++i) {
        A[i] = dist(rng);
        V[i] = A[i];
        cout << "? " << A[i] << endl;
    }

    // Read responses
    for (int i = 0; i < num_queries; ++i) {
        cin >> Times[i];
    }

    // Subtract the deterministic squaring costs from the total time
    // T(a) = Cost_sq(a) + Cost_mult(a)
    // We want to isolate Cost_mult(a)
    for (int i = 0; i < num_queries; ++i) {
        ull curr_a = A[i];
        long long sq_cost_sum = 0;
        for (int bit = 0; bit < 60; ++bit) {
            sq_cost_sum += mult_cost(curr_a, curr_a);
            curr_a = ((int128)curr_a * curr_a) % n;
        }
        Times[i] -= sq_cost_sum;
    }

    ull d = 0;
    // Determine d bit by bit from LSB (k=0) to MSB (k=59)
    for (int k = 0; k < 60; ++k) {
        int128 sum0 = 0, sumsq0 = 0;
        int128 sum1 = 0, sumsq1 = 0;

        // Calculate variance of residuals for both hypotheses
        // H0: d_k = 0
        // H1: d_k = 1
        for(int i=0; i<num_queries; ++i) {
            ull c = mult_cost(R[i], V[i]);
            long long t = Times[i];
            
            // Hypothesis 0: d_k = 0
            // Residual is t (assuming we subtracted nothing extra)
            sum0 += t;
            sumsq0 += (int128)t * t;
            
            // Hypothesis 1: d_k = 1
            // Residual is t - c (we attribute c to the current bit)
            long long t1 = t - c;
            sum1 += t1;
            sumsq1 += (int128)t1 * t1;
        }

        // We compare variances. Since Var(X) = E[X^2] - (E[X])^2,
        // we compare N*SumSq - Sum*Sum to avoid division and precision loss.
        // Lower variance implies the hypothesis fits the data better (less unexplained noise).
        int128 var_proxy0 = (int128)num_queries * sumsq0 - sum0 * sum0;
        int128 var_proxy1 = (int128)num_queries * sumsq1 - sum1 * sum1;

        int bit = 0;
        if (var_proxy1 < var_proxy0) {
            bit = 1;
        }
        
        // From problem statement: d is coprime to phi(n) = (p-1)(q-1).
        // Since p, q are odd primes, phi(n) is even.
        // Thus d must be odd. d_0 = 1.
        if (k == 0) bit = 1; 

        if (bit) {
            d |= (1ULL << k);
            // If d_k = 1, we update the residuals and the state R
            for (int i = 0; i < num_queries; ++i) {
                ull c = mult_cost(R[i], V[i]);
                Times[i] -= c;
                R[i] = ((int128)R[i] * V[i]) % n;
            }
        }
        // If d_k = 0, Times and R remain unchanged for the next step logic
        // (R doesn't get multiplied, Times doesn't lose the cost term)
        
        // Prepare V for next iteration (v_{k+1} = v_k^2)
        for (int i = 0; i < num_queries; ++i) {
            V[i] = ((int128)V[i] * V[i]) % n;
        }
    }

    cout << "! " << d << endl;

    return 0;
}