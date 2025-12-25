#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <numeric>

// Pre-computation for primes using a sieve
const int MAX_PRIME_SIEVE = 320; // sqrt(100000) is approx 316.2
std::vector<int> primes;
std::vector<bool> is_prime_sieve;

void sieve() {
    is_prime_sieve.assign(MAX_PRIME_SIEVE + 1, true);
    is_prime_sieve[0] = is_prime_sieve[1] = false;
    for (int p = 2; p * p <= MAX_PRIME_SIEVE; ++p) {
        if (is_prime_sieve[p]) {
            for (int i = p * p; i <= MAX_PRIME_SIEVE; i += p)
                is_prime_sieve[i] = false;
        }
    }
    for (int p = 2; p <= MAX_PRIME_SIEVE; ++p) {
        if (is_prime_sieve[p]) {
            primes.push_back(p);
        }
    }
}

// Main construction function based on affine planes
std::vector<std::pair<int, int>> construct(int N, int M) {
    // Find the largest prime p such that p*p <= M
    auto it = std::upper_bound(primes.begin(), primes.end(), static_cast<int>(sqrt(M)));
    int p = 0;
    if (it != primes.begin()) {
        p = *(--it);
    }

    // Fallback to a "cross" construction if no suitable prime is found (for small M)
    if (p == 0) {
        std::vector<std::pair<int, int>> points;
        if (N > 0 && M > 0) {
            points.reserve(N + M - 1);
            for (int c = 1; c <= M; ++c) {
                points.push_back({1, c});
            }
            for (int r = 2; r <= N; ++r) {
                points.push_back({r, 1});
            }
        }
        return points;
    }

    std::vector<std::pair<int, int>> points;
    long long p2 = static_cast<long long>(p) * p;
    
    // Use up to p^2+p lines from the affine plane AG(2,p)
    int N_used = std::min(N, static_cast<int>(p2 + p));
    points.reserve(N_used * p + (M > p2 ? M - p2 : 0));

    // Lines of type y = ax+b
    for (int r = 1; r <= std::min(N_used, static_cast<int>(p2)); ++r) {
        int r_idx = r - 1;
        int a = r_idx / p;
        int b = r_idx % p;
        for (int i = 0; i < p; ++i) {
            int j = (static_cast<long long>(a) * i + b) % p;
            points.push_back({r, i * p + j + 1});
        }
    }

    // Lines of type x = c
    if (N_used > p2) {
        for (int r = p2 + 1; r <= N_used; ++r) {
            int c_v = r - p2 - 1;
            for (int j = 0; j < p; ++j) {
                points.push_back({r, c_v * p + j + 1});
            }
        }
    }
    
    // Add points in remaining columns to row 1
    if (N > 0) {
        for (int c = p2 + 1; c <= M; ++c) {
            points.push_back({1, c});
        }
    }

    return points;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    sieve();

    int n, m;
    std::cin >> n >> m;

    auto points1 = construct(n, m);
    auto points2_raw = construct(m, n);

    if (points1.size() >= points2_raw.size()) {
        std::cout << points1.size() << "\n";
        for (const auto& p : points1) {
            std::cout << p.first << " " << p.second << "\n";
        }
    } else {
        std::cout << points2_raw.size() << "\n";
        for (const auto& p : points2_raw) {
            std::cout << p.second << " " << p.first << "\n";
        }
    }

    return 0;
}