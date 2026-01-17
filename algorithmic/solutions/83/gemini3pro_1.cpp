#include <iostream>
#include <vector>

using namespace std;

int main() {
    // Optimize standard I/O operations for performance
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // spf[i] stores the smallest prime factor of i
    // f[i] stores the value of the function f at i
    vector<int> spf(n + 1, 0);
    vector<int> f(n + 1);
    vector<int> primes;

    // Linear Sieve to compute smallest prime factors
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == 0) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > spf[i] || (long long)i * p > n) break;
            spf[i * p] = p;
        }
    }

    // Base case
    f[1] = 1;
    long long current_sum = 1;

    // Construct the function values
    for (int i = 2; i <= n; ++i) {
        if (spf[i] == i) {
            // i is a prime number
            // Greedy strategy: choose f[i] to counteract the current sum
            if (current_sum > 0) {
                f[i] = -1;
            } else {
                f[i] = 1;
            }
        } else {
            // i is composite
            // Use the completely multiplicative property: f(x*y) = f(x)*f(y)
            // f(i) = f(spf[i]) * f(i / spf[i])
            int p = spf[i];
            f[i] = f[p] * f[i / p];
        }
        current_sum += f[i];
    }

    // Output the result
    for (int i = 1; i <= n; ++i) {
        cout << f[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}