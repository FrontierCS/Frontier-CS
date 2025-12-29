#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <utility>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_orig, m_orig;
    std::cin >> n_orig >> m_orig;

    bool swapped = false;
    int n = n_orig, m = m_orig;
    if (n > m) {
        swapped = true;
        std::swap(n, m);
    }

    // Sieve for primes up to sqrt(100000) approx 316
    const int SIEVE_LIMIT = 320;
    std::vector<int> primes;
    if (n >= 4 || m >= 4) { // Only need primes if constructions are possible
        std::vector<bool> is_prime(SIEVE_LIMIT + 1, true);
        is_prime[0] = is_prime[1] = false;
        for (int p = 2; p * p <= SIEVE_LIMIT; ++p) {
            if (is_prime[p]) {
                for (int i = p * p; i <= SIEVE_LIMIT; i += p)
                    is_prime[i] = false;
            }
        }
        for (int p = 2; p <= SIEVE_LIMIT; ++p) {
            if (is_prime[p]) {
                primes.push_back(p);
            }
        }
    }


    std::vector<std::pair<int, int>> best_points;

    // Strategy 1: L-shape
    if (n + m - 1 > 0) {
        best_points.reserve(n + m - 1);
        for (int i = 1; i <= n; ++i) {
            best_points.push_back({i, 1});
        }
        for (int j = 2; j <= m; ++j) {
            best_points.push_back({1, j});
        }
    }
    
    // Strategy 2: Construction based on a prime p ~ sqrt(n)
    int sqrt_n = static_cast<int>(sqrt(n));
    auto it_n = std::upper_bound(primes.begin(), primes.end(), sqrt_n);
    if (it_n != primes.begin()) {
        int p_n = *(--it_n);
        std::vector<std::pair<int, int>> points1;
        long long n_p = n / p_n;
        long long m_p = m / p_n;
        if (n_p > 0 && m_p > 0) {
            points1.reserve(n_p * p_n * m_p);
            for(long long a = 0; a < n_p; ++a) {
                for(long long b = 0; b < p_n; ++b) {
                    for(long long c = 0; c < m_p; ++c) {
                        points1.push_back({(int)(a*p_n+b+1), (int)(c*p_n + (a*c+b)%p_n + 1)});
                    }
                }
            }
            if (points1.size() > best_points.size()) {
                best_points = std::move(points1);
            }
        }
    }

    // Strategy 3: Construction based on a prime p ~ sqrt(m)
    int sqrt_m = static_cast<int>(sqrt(m));
    auto it_m = std::upper_bound(primes.begin(), primes.end(), sqrt_m);
    if (it_m != primes.begin()) {
        int p_m = *(--it_m);
        std::vector<std::pair<int, int>> points2;
        long long n_p = n / p_m;
        long long m_p = m / p_m;
        if (n_p > 0 && m_p > 0) {
            points2.reserve(n_p * p_m * m_p);
            for(long long a = 0; a < m_p; ++a) {
                for(long long b = 0; b < p_m; ++b) {
                    for(long long c = 0; c < n_p; ++c) {
                         points2.push_back({(int)(c*p_m + (a*c+b)%p_m + 1), (int)(a*p_m+b+1)});
                    }
                }
            }
            if (points2.size() > best_points.size()) {
                best_points = std::move(points2);
            }
        }
    }


    std::cout << best_points.size() << "\n";
    for (const auto& p : best_points) {
        if (swapped) {
            std::cout << p.second << " " << p.first << "\n";
        } else {
            std::cout << p.first << " " << p.second << "\n";
        }
    }

    return 0;
}