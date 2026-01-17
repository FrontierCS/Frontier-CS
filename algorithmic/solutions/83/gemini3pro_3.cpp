#include <iostream>
#include <vector>

using namespace std;

// Maximum value for n as per constraints
const int MAXN = 1000005;

// Smallest Prime Factor array
int spf[MAXN];
// Array to store the function values f(i)
int f[MAXN];
// List of primes found so far
int primes[MAXN];
int p_cnt = 0;

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (cin >> n) {
        // Base case: f(1) = 1 because f is completely multiplicative
        f[1] = 1;
        
        // Track the current prefix sum
        long long current_sum = 1;

        // Iterate from 2 to n to determine f(i)
        // We use a linear sieve approach to find primes and calculate f values
        for (int i = 2; i <= n; ++i) {
            if (spf[i] == 0) {
                // i is a prime number
                spf[i] = i;
                primes[p_cnt++] = i;
                
                // Greedy strategy:
                // If the current sum is positive, choose -1 to reduce it.
                // If the current sum is non-positive, choose 1 to increase it.
                if (current_sum > 0) {
                    f[i] = -1;
                } else {
                    f[i] = 1;
                }
            } else {
                // i is composite
                // f(i) = f(p) * f(i/p) due to complete multiplicativity
                int p = spf[i];
                f[i] = f[p] * f[i / p];
            }

            // Update the prefix sum
            current_sum += f[i];

            // Sieve forward to mark smallest prime factors for multiples of i
            for (int j = 0; j < p_cnt; ++j) {
                int p = primes[j];
                // Check bounds
                if ((long long)i * p > n) break;
                
                spf[i * p] = p;
                
                // Ensure we only mark with the smallest prime factor (linear sieve logic)
                if (p == spf[i]) break;
            }
        }

        // Output the resulting sequence
        for (int i = 1; i <= n; ++i) {
            cout << f[i] << (i == n ? "" : " ");
        }
        cout << "\n";
    }
    return 0;
}