#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>

long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

long long query(long long q) {
    std::cout << "0 " << q << std::endl;
    long long response;
    std::cin >> response;
    return response;
}

void answer(long long ans) {
    std::cout << "1 " << ans << std::endl;
}

void factorize(long long n, std::map<long long, int>& prime_factors) {
    if (n == 0) return;
    for (long long i = 2; i * i <= n; ++i) {
        if (n % i == 0) {
            int count = 0;
            while (n % i == 0) {
                n /= i;
                count++;
            }
            prime_factors[i] = std::max(prime_factors[i], count);
        }
    }
    if (n > 1) {
        prime_factors[n] = std::max(prime_factors[n], 1);
    }
}

void solve() {
    std::map<long long, int> prime_factors;

    // Using a fixed seed ensures the same sequence of random numbers for each run,
    // which is important for reproducibility and debugging in competitive programming.
    std::mt19937_64 rng(1337);
    
    // Perform a number of queries with random large numbers.
    // 25 queries is a reasonable number, leaving a large margin under the 100-query limit.
    for (int i = 0; i < 25; ++i) {
        // Generate a random number Q in [1, 10^18].
        // std::mt19937_64 generates a 64-bit unsigned integer. We can take it modulo 10^18.
        long long q = rng(); 
        q = (q % (long long)1e18) + 1;
        
        long long g = query(q);
        if (g > 1) {
            factorize(g, prime_factors);
        }
    }

    long long d_found = 1;
    for (auto const& [p, exp] : prime_factors) {
        d_found *= (exp + 1);
    }
    
    // Heuristic for the final answer based on the divisors found.
    // For small d_found, d_found + 7 is a good guess to satisfy |ans - d| <= 7.
    // This covers cases where d is small, e.g. X is a prime or product of a few primes.
    // If we find nothing (d_found=1), this gives 8, which is valid for d in [1, 15].
    //
    // For larger d_found, d_found * 2 covers cases where one large prime factor was missed,
    // which would double the number of divisors. This aims for the relative error bound.
    // The crossover point where d*2 > d+7 is d=7.
    long long final_ans = std::max(d_found + 7, d_found * 2);
    answer(final_ans);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}