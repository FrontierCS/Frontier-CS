#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>

using namespace std;

const int MAXN = 1000005;
int spf[MAXN];
int f[MAXN];
int best_f[MAXN];

// Sieve to compute the Smallest Prime Factor for each number
void sieve(int n) {
    for (int i = 1; i <= n; ++i) spf[i] = i;
    for (int i = 2; i * i <= n; ++i) {
        if (spf[i] == i) { // i is prime
            for (int j = i * i; j <= n; j += i) {
                if (spf[j] == j) spf[j] = i;
            }
        }
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    sieve(n);

    long long best_max_abs = -1;
    mt19937 rng(1337); // Fixed seed for reproducibility
    
    // We run a few passes: deterministic greedy and randomized greedy
    // to find the sequence with the minimum maximum prefix sum.
    int iterations = 15; 

    for (int iter = 0; iter < iterations; ++iter) {
        long long current_sum = 0;
        long long current_max = 0;
        bool possible = true;
        
        f[1] = 1;
        current_sum = 1;
        current_max = 1;

        for (int i = 2; i <= n; ++i) {
            if (spf[i] == i) {
                // i is Prime: we can choose f(i)
                int choice;
                if (iter == 0) {
                    // Strategy 0: Deterministic Greedy
                    // If sum > 0, pick -1 to decrease sum.
                    // If sum <= 0, pick 1 to increase sum.
                    if (current_sum > 0) choice = -1;
                    else choice = 1;
                } else if (iter == 1) {
                    // Strategy 1: Slightly different tie-breaking
                    if (current_sum >= 0) choice = -1;
                    else choice = 1;
                } else {
                    // Randomized Greedy strategies
                    // Determine ideal direction
                    int target = (current_sum > 0) ? -1 : (current_sum < 0 ? 1 : 0);
                    
                    if (target == 0) {
                        choice = (rng() % 2) ? 1 : -1;
                    } else {
                        // With high probability pick target, allowing small exploration
                        if ((rng() % 100) < 95) choice = target;
                        else choice = -target;
                    }
                }
                f[i] = choice;
            } else {
                // i is Composite: f(i) is determined
                // f(i) = f(spf[i]) * f(i / spf[i])
                // Since spf[i] is prime, its value was chosen when we visited it.
                // i / spf[i] < i, so its value is already computed.
                int p = spf[i];
                f[i] = f[p] * f[i / p];
            }
            
            current_sum += f[i];
            long long abs_s = std::abs(current_sum);
            if (abs_s > current_max) current_max = abs_s;
            
            // Optimization: if this run is already worse or equal to the best found, abort.
            if (best_max_abs != -1 && current_max >= best_max_abs) {
                possible = false;
                break;
            }
        }

        if (possible) {
            best_max_abs = current_max;
            for (int k = 1; k <= n; ++k) best_f[k] = f[k];
            // If we found a very good solution, stop early.
            if (best_max_abs <= 2) break;
        }
    }

    // Output the best sequence found
    for (int i = 1; i <= n; ++i) {
        cout << best_f[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}