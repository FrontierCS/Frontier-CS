#include <iostream>
#include <vector>
#include <numeric>

const int N = 1000000;

int f[N + 1];
int spf[N + 1];
std::vector<int> primes;

void sieve() {
    for (int i = 2; i <= N; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > spf[i] || (long long)i * p > N) break;
            spf[i * p] = p;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // As per the problem statement, there is a single test case with n = 10^6.
    const int n = 1000000;
    
    sieve();

    f[1] = 1;
    long long current_sum = 1;

    for (int i = 2; i <= n; ++i) {
        if (spf[i] == i) { // i is prime
            if (current_sum > 0) {
                f[i] = -1;
            } else {
                f[i] = 1;
            }
        } else { // i is composite
            int p = spf[i];
            f[i] = f[p] * f[i / p];
        }
        current_sum += f[i];
    }

    for (int i = 1; i <= n; ++i) {
        std::cout << f[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}