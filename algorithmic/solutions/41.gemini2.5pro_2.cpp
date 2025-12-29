#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Sieve of Eratosthenes to generate primes up to a limit
const int SIEVE_LIMIT = 1500000;
std::vector<int> primes;
bool is_prime_sieve[SIEVE_LIMIT + 1];

void sieve() {
    std::fill(is_prime_sieve, is_prime_sieve + SIEVE_LIMIT + 1, true);
    is_prime_sieve[0] = is_prime_sieve[1] = false;
    for (int p = 2; p * p <= SIEVE_LIMIT; ++p) {
        if (is_prime_sieve[p]) {
            for (int i = p * p; i <= SIEVE_LIMIT; i += p)
                is_prime_sieve[i] = false;
        }
    }
    for (int p = 2; p <= SIEVE_LIMIT; ++p) {
        if (is_prime_sieve[p]) {
            primes.push_back(p);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    long long n;
    std::cin >> n;

    sieve();

    // Find the maximum possible length k for our prime-based construction.
    // Let g_i be a sequence of pairwise coprime integers. A good choice is the sequence of primes.
    // Let g_i = p_{i-2} for i=2, ..., k.
    // A BSU can be constructed as a_1, a_2=lcm(g_2,g_3), ..., a_{k-1}=lcm(g_{k-1},g_k), a_k.
    // With g_i as primes, lcm(g_i, g_{i+1}) = g_i * g_{i+1}.
    // To satisfy a_k > a_{k-1} and other constraints, we need (g_{k-1}+1)*g_k <= n.
    // In terms of primes, this is (p_{k-3}+1)*p_{k-2} <= n.
    // Let i = k-3. We find the maximum i satisfying this condition to find the maximum k.
    int max_i = -1;
    for (size_t i = 0; i + 1 < primes.size(); ++i) {
        if ((__int128)(primes[i] + 1) * primes[i+1] <= n) {
            max_i = i;
        } else {
            break;
        }
    }

    if (max_i == -1) {
        // Fallback for small n where our construction doesn't produce k>=3.
        // Powers of 2 form a simple and valid BSU.
        std::vector<long long> a;
        long long current = 1;
        while(current <= n) {
            a.push_back(current);
            if (n / 2 < current) break;
            current *= 2;
        }
        if (a.empty() && n > 0) {
            a.push_back(1);
        }
        
        if (a.empty()) { // Should not happen given constraints n>=1
             std::cout << 0 << "\n\n";
        } else {
            std::cout << a.size() << "\n";
            for (size_t i = 0; i < a.size(); ++i) {
                std::cout << a[i] << (i == a.size() - 1 ? "" : " ");
            }
            std::cout << "\n";
        }
        return 0;
    }

    int K = max_i + 3;
    std::vector<long long> a(K);
    
    // Construction using g_i = p_{i-2}
    // a_1 = c'*g_2 where c' < g_3 and gcd(c', g_3)=1. To maximize sum, we maximize c'.
    // With g_3=p_1=3, max c' is 2. So a_1 = (p_1-1)p_0.
    a[0] = (long long)(primes[1] - 1) * primes[0];
    
    // a_i = g_i * g_{i+1} = p_{i-2} * p_{i-1} for i=2..k-1
    for (int i = 1; i < K - 1; ++i) {
        a[i] = (long long)primes[i-1] * primes[i];
    }
    
    // a_k = c * g_k = c * p_{k-2}.
    // We maximize c s.t. a_k <= n, a_k > a_{k-1}, and gcd property holds.
    long long p_last = primes[K - 2];
    long long p_seclast = primes[K - 3];
    long long C_max = n / p_last;
    long long c = C_max;

    // We need gcd(c, g_{k-1}) = 1. Since g_{k-1} is prime p_{k-3}, we need c % p_{k-3} != 0.
    if (c % p_seclast == 0) {
        c--;
    }
    a[K-1] = c * p_last;

    std::cout << K << "\n";
    for (int i = 0; i < K; ++i) {
        std::cout << a[i] << (i == K - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}