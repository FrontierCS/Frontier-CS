#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>

// Sieve of Eratosthenes to find primes up to sqrt(100000)
const int SIEVE_LIMIT = 320;
std::vector<int> primes;
bool is_prime_sieve[SIEVE_LIMIT];

void sieve() {
    std::fill(is_prime_sieve, is_prime_sieve + SIEVE_LIMIT, true);
    is_prime_sieve[0] = is_prime_sieve[1] = false;
    for (int p = 2; p * p < SIEVE_LIMIT; ++p) {
        if (is_prime_sieve[p]) {
            for (int i = p * p; i < SIEVE_LIMIT; i += p)
                is_prime_sieve[i] = false;
        }
    }
    for (int p = 2; p < SIEVE_LIMIT; ++p) {
        if (is_prime_sieve[p]) {
            primes.push_back(p);
        }
    }
}

int largest_prime_le(int n) {
    if (n < 2) return 0;
    auto it = std::upper_bound(primes.begin(), primes.end(), n);
    --it;
    return *it;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    sieve();

    int n, m;
    std::cin >> n >> m;

    long long k_cross = 0;
    if (n > 0 && m > 0) {
        k_cross = (long long)n + m - 1;
    }

    long long k_geom1 = 0;
    int q1 = largest_prime_le(static_cast<int>(sqrt(m)));
    if (q1 > 0) {
        if (n <= (long long)q1 * q1 + q1) {
            k_geom1 = (long long)n * q1;
        }
    }

    long long k_geom2 = 0;
    int q2 = largest_prime_le(static_cast<int>(sqrt(n)));
    if (q2 > 0) {
        if (m <= (long long)q2 * q2 + q2) {
            k_geom2 = (long long)m * q2;
        }
    }

    if (k_cross >= k_geom1 && k_cross >= k_geom2) {
        std::cout << k_cross << "\n";
        for (int i = 1; i <= n; ++i) {
            std::cout << i << " " << 1 << "\n";
        }
        for (int j = 2; j <= m; ++j) {
            std::cout << 1 << " " << j << "\n";
        }
    } else if (k_geom1 >= k_geom2) {
        // Use n rows, m cols for geom
        int q = q1;
        long long k = (long long)n * q;
        std::cout << k << "\n";
        long long q_sq = (long long)q * q;
        for (int i = 1; i <= n; ++i) {
            if (i <= q_sq) {
                long long a = (i - 1) / q;
                long long b = (i - 1) % q;
                for (int x = 0; x < q; ++x) {
                    long long y = (a * x + b) % q;
                    long long col = x * q + y + 1;
                    std::cout << i << " " << col << "\n";
                }
            } else {
                long long c = (i - 1 - q_sq);
                for (int y = 0; y < q; ++y) {
                    long long x = c;
                    long long col = x * q + y + 1;
                    std::cout << i << " " << col << "\n";
                }
            }
        }
    } else {
        // Use m rows, n cols for geom, then transpose
        int q = q2;
        long long k = (long long)m * q;
        std::cout << k << "\n";
        long long q_sq = (long long)q * q;
        for (int i = 1; i <= m; ++i) {
            if (i <= q_sq) {
                long long a = (i - 1) / q;
                long long b = (i - 1) % q;
                for (int x = 0; x < q; ++x) {
                    long long y = (a * x + b) % q;
                    long long col = x * q + y + 1;
                    std::cout << col << " " << i << "\n";
                }
            } else {
                long long c = (i - 1 - q_sq);
                for (int y = 0; y < q; ++y) {
                    long long x = c;
                    long long col = x * q + y + 1;
                    std::cout << col << " " << i << "\n";
                }
            }
        }
    }

    return 0;
}