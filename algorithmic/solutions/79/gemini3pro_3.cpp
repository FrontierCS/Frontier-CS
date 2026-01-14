#include <iostream>
#include <vector>
#include <random>
#include <algorithm>

using namespace std;

typedef unsigned long long ull;
typedef unsigned __int128 u128;

// Function to calculate the number of bits in x without leading zeros.
// Formally: ceil(log2(x+1)). 
// bits(0)=0, bits(1)=1, bits(2)=2, bits(3)=2, bits(4)=3.
int get_bits(ull x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Function to calculate the cost of multiplying x and y modulo n.
// Time = (bits(x) + 1) * (bits(y) + 1)
ull mul_cost(ull x, ull y) {
    return (ull)(get_bits(x) + 1) * (get_bits(y) + 1);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ull n;
    // Read the modulus n provided by the interactor
    if (!(cin >> n)) return 0;

    // We can issue up to 30000 queries.
    // 25000 is sufficient to get very high statistical confidence.
    int queries = 25000;
    
    vector<ull> A(queries);
    vector<ull> T(queries);
    
    // Use a fixed seed for reproducibility, although any random seed works.
    mt19937_64 rng(1337);
    uniform_int_distribution<ull> dist(0, n - 1);

    // Perform queries
    // We send a query and immediately read the response to avoid buffer issues.
    for(int i = 0; i < queries; ++i) {
        A[i] = dist(rng);
        cout << "? " << A[i] << endl;
        cin >> T[i];
    }

    // Maintain the current state of 'a' and 'r' for each sample as we simulate the process
    vector<ull> cur_a = A;
    vector<ull> cur_r(queries, 1);
    
    // Residuals store the remaining time unaccounted for.
    // Initially, it's the total measured time.
    vector<double> residuals(queries);
    for(int i = 0; i < queries; ++i) {
        residuals[i] = (double)T[i];
    }

    ull d_final = 0;

    // We recover the bits of d from LSB (bit 0) to MSB (bit 59)
    for(int k = 0; k < 60; ++k) {
        // We use a correlation-based attack (essentially linear regression slope).
        // Let Y = residuals.
        // If d_k = 0, Y = Noise.
        // If d_k = 1, Y = Cost(cur_r, cur_a) + Noise.
        // We define C = Cost(cur_r, cur_a).
        // If d_k = 1, Y correlates with C with slope ~1.
        // If d_k = 0, Y is uncorrelated with C (slope ~0).
        
        double sum_C = 0;
        double sum_Y = 0;
        vector<double> C(queries);

        for(int i = 0; i < queries; ++i) {
            // The squaring step 'a = a * a % n' happens regardless of d_k.
            // We can calculate its cost exactly and subtract it from the residual to reduce variance.
            ull sq_cost = mul_cost(cur_a[i], cur_a[i]);
            residuals[i] -= sq_cost;

            // Calculate the hypothetical cost if the k-th bit were 1 (r = r * a % n)
            ull m_cost = mul_cost(cur_r[i], cur_a[i]);
            C[i] = (double)m_cost;

            sum_C += C[i];
            sum_Y += residuals[i];
        }

        double mean_C = sum_C / queries;
        double mean_Y = sum_Y / queries;

        double num = 0;
        double den = 0;

        // Compute slope of regression line of Y on C
        for(int i = 0; i < queries; ++i) {
            double diff_C = C[i] - mean_C;
            double diff_Y = residuals[i] - mean_Y;
            num += diff_C * diff_Y;
            den += diff_C * diff_C;
        }

        double slope = (den == 0) ? 0 : num / den;

        // If slope is closer to 1, the bit is likely 1. If closer to 0, likely 0.
        int bit = (slope > 0.5) ? 1 : 0;

        if (bit) {
            d_final |= (1ULL << k);
        }

        // Update the state for the next bit
        for(int i = 0; i < queries; ++i) {
            if (bit) {
                // If the bit was 1, the multiplication r = r * a occurred.
                // Subtract this cost from residuals.
                residuals[i] -= C[i];
                // Update r
                cur_r[i] = (u128)cur_r[i] * cur_a[i] % n;
            }
            // Update a to a^2 (mod n) for the next iteration
            cur_a[i] = (u128)cur_a[i] * cur_a[i] % n;
        }
    }

    cout << "! " << d_final << endl;

    return 0;
}