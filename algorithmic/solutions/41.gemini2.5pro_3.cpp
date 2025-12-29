#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    long long n;
    std::cin >> n;

    __int128_t best_V = 0;
    long long best_a1 = 0, best_c = 0, best_k = 0;

    // Baseline: a sequence of length 1. To maximize V = 1 * a1, we take a1 = n.
    best_V = n;
    best_k = 1;
    best_a1 = n;
    best_c = 2; // doesn't matter for k=1, but needs a value > 1 for sequence generation

    // Heuristic: search for the best geometric progression
    // a_i = a_1 * c^(i-1)
    for (long long c = 2; c <= 400; ++c) {
        __int128_t p = c; // p will be c^(k-1), starting with k=2
        for (long long k = 2; k <= 62; ++k) {
            if (p > n) {
                break;
            }
            long long a1 = n / (long long)p;
            if (a1 == 0) {
                break;
            }

            __int128_t p_k;
            // Check for overflow before computing c^k
            if (__builtin_mul_overflow(p, c, &p_k)) {
                 break;
            }

            __int128_t sum_geom_series_ratio = (p_k - 1) / (c - 1);
            __int128_t sum = (__int128_t)a1 * sum_geom_series_ratio;
            __int128_t current_V = (__int128_t)k * sum;
            
            if (current_V > best_V) {
                best_V = current_V;
                best_a1 = a1;
                best_c = c;
                best_k = k;
            }
            
            // Prepare for next k, check for overflow before p *= c
            if (p > (__int128_t)n / c) { 
                break;
            }
            p *= c;
        }
    }

    std::cout << best_k << std::endl;
    if (best_k > 0) {
        __int128_t current_term = best_a1;
        for (int i = 0; i < best_k; ++i) {
            std::cout << (long long)current_term << (i == best_k - 1 ? "" : " ");
            if (i < best_k - 1) {
                current_term *= best_c;
            }
        }
    }
    std::cout << std::endl;

    return 0;
}