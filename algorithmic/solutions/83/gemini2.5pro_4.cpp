#include <iostream>
#include <vector>

const int N = 1000000;

// Using global arrays to avoid stack overflow, common in competitive programming
// for large N. They are zero-initialized.
int spf[N + 1];
int f[N + 1];

// Sieve to compute smallest prime factor for every number up to N
void sieve() {
    for (int i = 0; i <= N; ++i) {
        spf[i] = i;
    }
    for (int i = 2; i * i <= N; ++i) {
        if (spf[i] == i) { // i is a prime
            for (int j = i * i; j <= N; j += i) {
                if (spf[j] == j) { // if j's spf is not set yet
                    spf[j] = i;
                }
            }
        }
    }
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    sieve();

    const int n = N;

    // f(1) must be 1 for a completely multiplicative function where |f(i)|=1
    f[1] = 1;
    long long current_sum = 1;

    // Iterate from 2 to n to define f(i)
    for (int i = 2; i <= n; ++i) {
        int p = spf[i];
        if (p == i) { // i is a prime number
            // This is our only point of choice. We make a greedy decision.
            // Choose f(i) to steer the partial sum S_i towards 0.
            if (current_sum > 0) {
                f[i] = -1;
            } else {
                // This covers current_sum <= 0, including the tie-breaking case current_sum = 0.
                f[i] = 1;
            }
        } else { // i is a composite number
            // f is completely multiplicative, so f(i) = f(p) * f(i/p).
            // Since p=spf[i]<=i and i/p < i, f(p) and f(i/p) have already been computed.
            f[i] = f[p] * f[i / p];
        }
        current_sum += f[i];
    }

    // Output the resulting function values
    for (int i = 1; i <= n; ++i) {
        std::cout << f[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}