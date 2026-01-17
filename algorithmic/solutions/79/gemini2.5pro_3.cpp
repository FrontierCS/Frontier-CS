#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>
#include <chrono>

// The modulo for the device's computation.
long long n;

// Custom modular multiplication using __int128 to prevent overflow,
// as a*b can exceed the capacity of a 64-bit integer.
long long mul(long long a, long long b, long long m) {
    return static_cast<long long>((static_cast<__int128>(a) * b) % m);
}

// Computes the number of bits in the binary representation of x.
// For x > 0, this is floor(log2(x)) + 1. For x = 0, it's 0.
// __builtin_clzll counts leading zeros for a 64-bit long long.
int bits(long long x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Sends a query to the device with value 'a' and returns the measured time.
long long get_time(long long a) {
    std::cout << "? " << a << std::endl;
    long long time;
    std::cin >> time;
    return time;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Read the public modulus n.
    std::cin >> n;

    // The secret exponent d to be determined. We will find its bits one by one.
    long long d = 0;

    // A random number generator for selecting inputs 'a'.
    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    // Determine each bit of d from 0 to 59.
    for (int k = 0; k < 60; ++k) {
        long double score = 0;
        // Number of random samples 'a' to use for determining each bit.
        // A higher number increases accuracy at the cost of more queries.
        int num_samples = 40;

        for (int s = 0; s < num_samples; ++s) {
            long long a_base = std::uniform_int_distribution<long long>(2, n - 1)(rng);
            
            long long total_time = get_time(a_base);

            // Precompute the sequence a_i = a^(2^i) mod n and their bit counts.
            std::vector<long long> a_seq(60);
            std::vector<int> a_bits(60);
            a_seq[0] = a_base;
            for (int i = 1; i < 60; ++i) {
                a_seq[i] = mul(a_seq[i - 1], a_seq[i - 1], n);
            }
            for (int i = 0; i < 60; ++i) {
                a_bits[i] = bits(a_seq[i]) + 1;
            }

            // Calculate C(a), the part of the cost independent of d.
            long long C_a = 0;
            for (int i = 0; i < 60; ++i) {
                C_a += (long long)a_bits[i] * a_bits[i];
            }

            long long d_lt_k = d; // Bits of d determined so far.
            
            // Calculate D_known, the part of the cost from known bits of d.
            // Also, track the value of 'r' through the first k steps.
            long long D_known = 0;
            long long current_r = 1;
            for (int i = 0; i < k; ++i) {
                if ((d_lt_k >> i) & 1) {
                    D_known += (long long)(bits(current_r) + 1) * a_bits[i];
                    current_r = mul(current_r, a_seq[i], n);
                }
            }
            long long r_k = current_r;

            // T_rem is the remaining time, corresponding to the unknown bits of d.
            long long T_rem = total_time - C_a - D_known;
            
            // V_k is the cost contribution if the k-th bit of d is 1.
            long long V_k = (long long)(bits(r_k) + 1) * a_bits[k];
            
            // The core of the statistical test. If d_k is 0, T_rem is just noise from higher bits.
            // If d_k is 1, T_rem is V_k plus noise. On average, T_rem should be larger if d_k=1.
            // We test if T_rem is greater than V_k/2. A positive score favors d_k=1.
            score += T_rem - (long double)V_k / 2.0;
        }

        // If the average score over all samples is positive, we conclude that d_k is 1.
        if (score > 0) {
            d |= (1LL << k);
        }
    }

    // Output the final determined value of d.
    std::cout << "! " << d << std::endl;

    return 0;
}