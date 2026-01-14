#include <iostream>
#include <vector>

const int MAXN = 1000000;

// lp[i] stores the least prime factor of i.
int lp[MAXN + 1];
// A vector to store all prime numbers up to n.
std::vector<int> primes;
// f[i] stores the value of the function f(i).
int f[MAXN + 1];

// A linear sieve to compute the least prime factor for all numbers up to n.
void sieve(int n) {
    for (int i = 2; i <= n; ++i) {
        if (lp[i] == 0) {
            lp[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > lp[i] || (long long)i * p > n) {
                break;
            }
            lp[i * p] = p;
        }
    }
}

int main() {
    // Fast I/O is crucial for large n.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    sieve(n);

    // For a completely multiplicative function with |f(i)|=1, f(1) must be 1.
    f[1] = 1;
    long long current_sum = 1;

    for (int i = 2; i <= n; ++i) {
        // At the start of this iteration, current_sum is the sum up to i-1.
        if (lp[i] == i) { // i is a prime number.
            // Greedily choose f(i) to minimize |current_sum + f(i)|.
            if (current_sum > 0) {
                f[i] = -1;
            } else { // This handles current_sum <= 0.
                f[i] = 1;
            }
        } else { // i is a composite number.
            // f(i) is determined by its prime factors due to complete multiplicativity.
            // f(i) = f(lp[i]) * f(i / lp[i]).
            f[i] = f[lp[i]] * f[i / lp[i]];
        }
        // Update the sum to include f(i).
        current_sum += f[i];
    }
    
    // Print the constructed sequence f(1), ..., f(n).
    for (int i = 1; i <= n; ++i) {
        std::cout << f[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}