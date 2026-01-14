#include <iostream>
#include <vector>
#include <cmath>
#include <chrono>
#include <random>
#include <numeric>

// Use __int128 for intermediate products to avoid overflow.
// This is a GCC/Clang extension, standard in competitive programming environments.
using int128 = __int128_t;

// The modulus, read from input.
long long n;

// Calculates bits(x) = ceil(log2(x+1)).
// For a positive integer x, this is the number of bits in its binary representation.
inline int bits(long long x) {
    if (x == 0) {
        return 0;
    }
    // For a 64-bit non-zero integer, the number of bits is 64 - (number of leading zeros).
    // __builtin_clzll is a GCC/Clang intrinsic for "count leading zeros".
    return 64 - __builtin_clzll(x);
}

// Function to simulate the device's computation and calculate the total time.
// This function must correctly model the timing behavior described in the problem.
long long calculate_time(long long a_in, long long d) {
    long long total_time = 0;
    int128 r = 1;
    int128 cur_a = a_in;

    for (int i = 0; i < 60; ++i) {
        if ((d >> i) & 1) {
            total_time += (long long)(bits((long long)r) + 1) * (bits((long long)cur_a) + 1);
            r = r * cur_a % n;
        }
        total_time += (long long)(bits((long long)cur_a) + 1) * (bits((long long)cur_a) + 1);
        cur_a = cur_a * cur_a % n;
    }
    return total_time;
}

int main() {
    // Fast I/O is crucial for interactive problems.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Read the public modulus n.
    std::cin >> n;

    // From the problem description, d is chosen coprime with m = (p-1)(q-1).
    // Since p and q are primes > 2, p-1 and q-1 are even.
    // Thus m is divisible by 4.
    // For d to be coprime with m, d must be odd.
    // This implies the 0-th bit of d is always 1. We start with this knowledge.
    long long d_candidate = 1;

    // Initialize a high-quality random number generator.
    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    std::uniform_int_distribution<long long> distrib(2, n - 1);

    // We need to determine 59 bits (from 1 to 59).
    // With a 30000 query limit, we can afford a good number of samples for each bit.
    // Let's use 400 samples per bit, for a total of 59 * 400 = 23600 queries.
    int samples_per_bit = 400;

    // Determine bits one by one, from k=1 to k=59.
    for (int k = 1; k < 60; ++k) {
        long double score_diff_sum = 0;
        
        // At step k, d_candidate holds our best guess for d mod 2^k.
        // We form two hypotheses for d mod 2^(k+1).
        long long d_hyp0 = d_candidate;              // Hypothesis: k-th bit is 0.
        long long d_hyp1 = d_candidate | (1LL << k); // Hypothesis: k-th bit is 1.

        for (int j = 0; j < samples_per_bit; ++j) {
            // Choose a random base 'a'.
            long long a = distrib(rng);
            
            // Query the device and get the execution time.
            std::cout << "? " << a << std::endl;
            long long observed_time;
            std::cin >> observed_time;

            // Calculate the expected time for both hypotheses, using only the bits known so far.
            long long time_hyp0 = calculate_time(a, d_hyp0);
            long long time_hyp1 = calculate_time(a, d_hyp1);
            
            // Calculate the squared error for both hypotheses.
            int128 diff0 = observed_time - time_hyp0;
            int128 diff1 = observed_time - time_hyp1;
            
            // Accumulate the difference of squared errors.
            // If d_k=0 is correct, observed_time should be closer to time_hyp0, making diff0^2 < diff1^2.
            // If d_k=1 is correct, observed_time should be closer to time_hyp1, making diff0^2 > diff1^2.
            score_diff_sum += (long double)diff0 * diff0 - (long double)diff1 * diff1;
        }
        
        // If the sum of score differences is positive, it's statistically more likely that d_k=1.
        if (score_diff_sum > 0) {
            d_candidate = d_hyp1;
        }
    }

    // Output the final determined value of d.
    std::cout << "! " << d_candidate << std::endl;

    return 0;
}