#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <string>

// It's a heuristic problem, so I'll try two different constructions
// and take the one that gives a better objective value.

// Construction 1: Geometric progression with ratio 2
// a_i = x * 2^(i-1)
// gcd(a_i, a_{i-1}) = x * 2^(i-2), which is a strictly increasing sequence.

// Construction 2: Product of consecutive primes
// a_i = x * p_{i-1} * p_i
// gcd(a_i, a_{i-1}) = x * p_{i-1}, which is a strictly increasing sequence.

// Using __int128 for objective value as it can exceed 2^64-1.
using int128 = __int128;

// Sieve for primes up to sqrt(10^12) = 10^6
const int SIEVE_LIMIT = 1000000 + 100;
std::vector<long long> primes;
bool is_prime[SIEVE_LIMIT];

void sieve() {
    std::fill(is_prime, is_prime + SIEVE_LIMIT, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p < SIEVE_LIMIT; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i < SIEVE_LIMIT; i += p)
                is_prime[i] = false;
        }
    }
    for (int p = 2; p < SIEVE_LIMIT; ++p) {
        if (is_prime[p]) {
            primes.push_back(p);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    sieve();

    long long n;
    std::cin >> n;

    // Default valid BSU: k=1, a_1=n
    long long best_k = 1;
    long long best_x = n;
    int best_method = 0; // 0 for default, 1 for powers of 2, 2 for primes
    int128 max_v = n;

    // Method 1: Powers of 2
    for (int k = 1; k < 63; ++k) {
        int128 p = 1;
        if (k > 1) {
            unsigned long long temp_p = 1ULL << (k - 1);
            if (temp_p > (unsigned long long)n) break;
            p = temp_p;
        }

        if (p > n) break;
        long long x = n / (long long)p;
        if (x == 0) break;
        
        int128 sum_a = (int128)x * ((int128)1 << k) - (int128)x;
        
        int128 v = (int128)k * sum_a;
        if (v > max_v) {
            max_v = v;
            best_method = 1;
            best_k = k;
            best_x = x;
        }
    }

    // Method 2: Prime products
    int k_max = 0;
    if (primes.size() >= 2) {
        int low = 1, high = primes.size() - 2;
        while(low <= high) {
            int mid = low + (high-low)/2;
            if ((int128)primes[mid-1] * primes[mid] > n) {
                high = mid - 1;
            } else {
                k_max = mid;
                low = mid + 1;
            }
        }
    }

    if (k_max > 0) {
        std::vector<int128> pref_sum(k_max + 1, 0);
        for(int i = 0; i < k_max; ++i) {
            pref_sum[i+1] = pref_sum[i] + (int128)primes[i] * primes[i+1];
        }

        for (int k = std::max(1, k_max - 500); k <= k_max; ++k) {
            int128 last_prod = (int128)primes[k-1] * primes[k];
            if (last_prod > n) continue;

            long long x = n / (long long)last_prod;
            if (x == 0) continue;
            
            int128 sum_a = (int128)x * pref_sum[k];
            int128 v = (int128)k * sum_a;
            if (v > max_v) {
                max_v = v;
                best_method = 2;
                best_k = k;
                best_x = x;
            }
        }
    }

    // Output
    std::cout << best_k << "\n";
    if (best_method == 0) {
        std::cout << best_x << "\n";
    } else if (best_method == 1) {
        unsigned long long term = best_x;
        for (int i = 0; i < best_k; ++i) {
            std::cout << term << (i == best_k - 1 ? "" : " ");
            term *= 2;
        }
        std::cout << "\n";
    } else { // best_method == 2
        for (int i = 0; i < best_k; ++i) {
            int128 term = (int128)best_x * primes[i] * primes[i+1];
            std::cout << (long long)term << (i == best_k - 1 ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}