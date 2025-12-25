#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>

// Use unsigned 128-bit integers for modular multiplication to avoid overflow
using u64 = uint64_t;
using u128 = unsigned __int128;

u64 n;

// Function to calculate bits(x) = ceil(log2(x+1))
// For x > 0, this is the number of bits in binary representation.
// This can be computed efficiently using hardware instructions.
int bits(u64 x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

// Modular multiplication for 64-bit numbers using 128-bit intermediate type
u64 mul(u64 a, u64 b) {
    return (u128)a * b % n;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    // Use a fixed number of queries, well within the 30000 limit.
    // This provides ample data for the statistical approach.
    const int total_queries = 24000;

    std::vector<u64> a_samples(total_queries);
    std::vector<long long> T_obs(total_queries);

    // Use a seeded random number generator for reproducibility.
    // std::random_device provides a non-deterministic seed if available.
    std::mt19937_64 rng(std::random_device{}());
    std::uniform_int_distribution<u64> distrib(2, n - 1);

    // Perform all queries upfront
    for (int i = 0; i < total_queries; ++i) {
        a_samples[i] = distrib(rng);
        std::cout << "? " << a_samples[i] << std::endl;
        std::cin >> T_obs[i];
    }

    // Precompute powers of a and their bit lengths to speed up the main loop
    std::vector<std::vector<u64>> a_powers(total_queries, std::vector<u64>(60));
    std::vector<std::vector<int>> a_bits(total_queries, std::vector<int>(60));
    std::vector<long long> T_base(total_queries, 0);

    for (int j = 0; j < total_queries; ++j) {
        u64 cur_a = a_samples[j];
        for (int i = 0; i < 60; ++i) {
            a_powers[j][i] = cur_a;
            a_bits[j][i] = bits(cur_a) + 1;
            T_base[j] += (long long)a_bits[j][i] * a_bits[j][i];
            cur_a = mul(cur_a, cur_a);
        }
    }

    u64 d = 0;
    std::vector<u64> r(total_queries, 1);
    std::vector<long long> C(total_queries, 0);

    // Determine bits of d one by one, from d_0 to d_59
    for (int k = 0; k < 60; ++k) {
        long double sum_yv = 0;
        long double sum_v2 = 0;
        
        // Use all queries to determine each bit
        for (int j = 0; j < total_queries; ++j) {
            long long y = T_obs[j] - T_base[j] - C[j];
            long long v = (long long)a_bits[j][k] * (bits(r[j]) + 1);
            sum_yv += (long double)y * v;
            sum_v2 += (long double)v * v;
        }

        long double beta = 0;
        if (sum_v2 > 1e-12) { // Avoid division by zero
            beta = sum_yv / sum_v2;
        }

        int d_k = (beta > 0.5);
        
        if (d_k) {
            d |= (1ULL << k);
        }

        if (k < 59) {
            // Update C and r for the next iteration based on the bit we just found
            if (d_k) {
                for (int j = 0; j < total_queries; ++j) {
                     C[j] += (long long)a_bits[j][k] * (bits(r[j]) + 1);
                     r[j] = mul(r[j], a_powers[j][k]);
                }
            }
        }
    }

    std::cout << "! " << d << std::endl;

    return 0;
}