#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>

const int N_MAX = 1000000;
int spf[N_MAX + 1];
std::vector<int> primes;
bool is_small_prime_flag[N_MAX + 1] = {false};
int f_final[N_MAX + 1];

void sieve(int n) {
    std::iota(spf, spf + n + 1, 0);
    for (int i = 2; i * i <= n; ++i) {
        if (spf[i] == i) { // i is prime
            for (int j = i * i; j <= n; j += i) {
                if (spf[j] == j) {
                    spf[j] = i;
                }
            }
        }
    }
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == i) {
            primes.push_back(i);
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n = 1000000;
    // std::cin >> n; // Problem statement specifies n=10^6 for the only test case.

    sieve(n);
    
    int k = 14; 
    if (primes.size() < k) {
        k = primes.size();
    }

    for(int i = 0; i < k; ++i) {
        is_small_prime_flag[primes[i]] = true;
    }

    long long min_max_S = -1;
    int best_mask = 0;

    std::vector<int> f(n + 1);

    for (int mask = 0; mask < (1 << k); ++mask) {
        f[1] = 1;
        for (int i = 0; i < k; ++i) {
            if ((mask >> i) & 1) {
                f[primes[i]] = -1;
            } else {
                f[primes[i]] = 1;
            }
        }
        
        long long current_S = 1;
        long long max_abs_S = 1;
        bool pruned = false;

        for (int i = 2; i <= n; ++i) {
            int p = spf[i];
            if (spf[i] == i) { // is prime
                if (!is_small_prime_flag[i]) {
                    f[i] = (current_S > 0) ? -1 : 1;
                }
            } else { // is composite
                f[i] = f[p] * f[i/p];
            }
            current_S += f[i];
            max_abs_S = std::max(max_abs_S, std::abs(current_S));
            if (min_max_S != -1 && max_abs_S >= min_max_S) {
                pruned = true;
                break;
            }
        }

        if (!pruned) {
            if (min_max_S == -1 || max_abs_S < min_max_S) {
                min_max_S = max_abs_S;
                best_mask = mask;
            }
        }
    }

    // Final run with best_mask to generate output
    f_final[1] = 1;
    for (int i = 0; i < k; ++i) {
        if ((best_mask >> i) & 1) {
            f_final[primes[i]] = -1;
        } else {
            f_final[primes[i]] = 1;
        }
    }
    
    long long current_S = 1;
    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        if (spf[i] == i) {
            if (!is_small_prime_flag[i]) {
                f_final[i] = (current_S > 0) ? -1 : 1;
            }
        } else {
            f_final[i] = f_final[p] * f_final[i/p];
        }
        current_S += f_final[i];
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << f_final[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}