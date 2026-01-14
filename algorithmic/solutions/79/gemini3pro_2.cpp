#include <iostream>
#include <vector>
#include <random>
#include <algorithm>

using namespace std;

typedef unsigned long long ull;
typedef unsigned __int128 u128;

// Function to calculate bits(x) = ceil(log2(x+1))
// This is equivalent to the bit width of the integer.
int get_bits(ull x) {
    if (x == 0) return 0;
    int b = 0;
    while (x > 0) {
        x >>= 1;
        b++;
    }
    return b;
}

// Cost function as defined in the problem
int get_cost(ull x, ull y) {
    return (get_bits(x) + 1) * (get_bits(y) + 1);
}

// Modular multiplication using __int128 to prevent overflow
ull mul(ull a, ull b, ull n) {
    return (ull)((u128)a * b % n);
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    ull n;
    if (!(cin >> n)) return 0;

    // Number of samples. 600 is sufficient for high statistical confidence.
    // Allowed queries are 30000.
    int M = 600;
    
    vector<ull> queries(M);
    vector<long long> times(M);
    
    // Random number generator
    mt19937_64 rng(5489u);

    // Step 1: Collect measurements
    for (int i = 0; i < M; ++i) {
        ull a = rng() % n;
        queries[i] = a;
        cout << "? " << a << endl;
        cin >> times[i];
    }

    // Step 2: Precompute powers a^(2^j) and remove deterministic costs
    // a_pow[i][j] stores (queries[i]^(2^j)) % n
    vector<vector<ull>> a_pow(M, vector<ull>(60));
    for (int i = 0; i < M; ++i) {
        ull curr = queries[i];
        long long always_cost = 0;
        for (int j = 0; j < 60; ++j) {
            a_pow[i][j] = curr;
            // The 'always' part: a = a*a % n
            always_cost += get_cost(curr, curr);
            curr = mul(curr, curr, n);
        }
        times[i] -= always_cost;
    }

    ull d = 0;
    vector<ull> r(M, 1);

    // Step 3: Determine bits of d sequentially
    for (int k = 0; k < 60; ++k) {
        // We use a correlation attack to determine d_k.
        // We correlate the residual time (normalized) with the expected cost term.
        
        double sumX = 0, sumZ = 0;
        vector<double> X(M), Z(M);
        
        for (int i = 0; i < M; ++i) {
            // Predictor: The bit-size part of 'a' in the cost term
            X[i] = get_bits(a_pow[i][k]) + 1;
            
            // Normalizer: The bit-size part of 'r'. 
            // The cost term is (bits(r)+1)*(bits(a)+1).
            // Dividing by (bits(r)+1) isolates the dependency on 'a'.
            int b_r = get_bits(r[i]) + 1;
            
            // Normalized residual time
            Z[i] = (double)times[i] / b_r;
            
            sumX += X[i];
            sumZ += Z[i];
        }
        
        double meanX = sumX / M;
        double meanZ = sumZ / M;
        double cov = 0;
        
        for (int i = 0; i < M; ++i) {
            cov += (X[i] - meanX) * (Z[i] - meanZ);
        }
        
        // If d_k is 1, there's a positive correlation.
        // If d_k is 0, correlation is close to 0 (noise).
        // Threshold selected based on variance analysis (Signal ~ 2*M, Noise std dev small).
        if (cov > 1.0 * M) { 
            d |= (1ULL << k);
            
            // If d_k is 1, we must update the state:
            // 1. Subtract the cost of this multiplication from residual time.
            // 2. Update r = r * a % n.
            for (int i = 0; i < M; ++i) {
                times[i] -= get_cost(r[i], a_pow[i][k]);
                r[i] = mul(r[i], a_pow[i][k], n);
            }
        }
        // If d_k is 0, r doesn't change and the cost term wasn't part of the time, so no update.
    }

    cout << "! " << d << endl;

    return 0;
}