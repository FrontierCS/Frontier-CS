#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

// Sieve of Eratosthenes to find primes up to a limit
std::vector<int> primes;
const int SIEVE_LIMIT = 1000;

void sieve() {
    std::vector<bool> is_prime_sieve(SIEVE_LIMIT + 1, true);
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

long long query(long long q) {
    std::cout << "0 " << q << std::endl;
    long long response;
    std::cin >> response;
    return response;
}

void answer(long long ans) {
    std::cout << "1 " << ans << std::endl;
}

void solve() {
    long long ans = 1;
    
    // First 30 primes (up to 113)
    int small_primes_count = 0;
    for(size_t i = 0; i < primes.size(); ++i) {
        if (primes[i] <= 113) {
            small_primes_count++;
        } else {
            break;
        }
    }
    
    for (int i = 0; i < small_primes_count; ++i) {
        int p = primes[i];
        long long q = p;
        while (q <= 1000000000LL / p) {
            q *= p;
        }
        q *= p;

        long long g = query(q);
        int count = 0;
        if (g > 1) {
            while (g % p == 0) {
                g /= p;
                count++;
            }
        }
        ans *= (count + 1);
    }
    
    // Larger primes up to 1000
    std::vector<int> large_p_candidates;
    std::vector<std::vector<int>> groups;
    std::vector<int> current_group;
    long long current_prod = 1;
    
    for (size_t i = small_primes_count; i < primes.size(); ++i) {
        int p = primes[i];
        if (current_prod > 1000000000000000000LL / p) {
            groups.push_back(current_group);
            current_group.clear();
            current_prod = 1;
        }
        current_group.push_back(p);
        current_prod *= p;
    }
    if (!current_group.empty()) {
        groups.push_back(current_group);
    }
    
    for (const auto& group : groups) {
        long long q = 1;
        for (int p : group) {
            q *= p;
        }
        long long g = query(q);
        if (g > 1) {
            for (int p : group) {
                if (g % p == 0) {
                    large_p_candidates.push_back(p);
                }
            }
        }
    }
    
    std::sort(large_p_candidates.begin(), large_p_candidates.end());
    large_p_candidates.erase(std::unique(large_p_candidates.begin(), large_p_candidates.end()), large_p_candidates.end());

    for (int p : large_p_candidates) {
        long long q = p;
        while (q <= 1000000000LL / p) {
            q *= p;
        }
        q *= p;

        long long g = query(q);
        int count = 0;
        if (g > 1) {
            while (g % p == 0) {
                g /= p;
                count++;
            }
        }
        ans *= (count + 1);
    }

    answer(ans * 2);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    sieve();
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}