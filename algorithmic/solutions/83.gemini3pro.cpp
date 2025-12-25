#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Maximum value of N as per constraints
const int MAXN = 1000005;

// Global arrays
int spf[MAXN];      // Smallest Prime Factor
int ans[MAXN];      // Stores the best sequence found
int current_f[MAXN]; // Stores the sequence for the current iteration
int N;

// Sieve of Eratosthenes to precompute Smallest Prime Factor (SPF)
void sieve() {
    for (int i = 1; i <= N; i++) spf[i] = i;
    for (int i = 2; i * i <= N; i++) {
        if (spf[i] == i) { // i is prime
            for (int j = i * i; j <= N; j += i) {
                if (spf[j] == j) spf[j] = i;
            }
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    sieve();

    // Run 1: Deterministic Greedy Strategy
    // At each prime, choose f(p) to minimize the absolute value of the current prefix sum.
    // If sum > 0, choose -1; if sum < 0, choose 1; if sum == 0, choose -1.
    
    long long current_sum = 0;
    long long max_abs = 0;
    current_f[1] = 1;
    current_sum = 1;
    max_abs = 1;
    
    for (int i = 2; i <= N; i++) {
        if (spf[i] == i) { // i is Prime
            if (current_sum > 0) current_f[i] = -1;
            else if (current_sum < 0) current_f[i] = 1;
            else current_f[i] = -1; // Tie-breaking preference
        } else { // i is Composite
            int p = spf[i];
            // f(i) = f(p) * f(i/p). Since p < i and i/p < i, these are already computed.
            current_f[i] = current_f[p] * current_f[i/p];
        }
        
        current_sum += current_f[i];
        long long abs_s = std::abs(current_sum);
        if (abs_s > max_abs) max_abs = abs_s;
    }
    
    // Store the deterministic result as the initial best answer
    long long best_max_abs = max_abs;
    for(int i = 1; i <= N; ++i) ans[i] = current_f[i];
    
    // Run 2: Randomized Greedy with Restarts (Hill Climbing / Sampling)
    // We try to find a better sequence by introducing randomness when the partial sum is small.
    // We run this until we approach the time limit.
    
    mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    auto start_time = std::chrono::steady_clock::now();
    
    while (true) {
        auto curr_time = std::chrono::steady_clock::now();
        // Time limit safety check (stop after 800ms)
        if (std::chrono::duration_cast<std::chrono::milliseconds>(curr_time - start_time).count() > 800) break;
        
        // "Width" determines the range around 0 where we allow random moves.
        // If |current_sum| <= width, we pick randomly. Otherwise, we greedily correct.
        int width = rng() % 3; // 0, 1, or 2
        
        current_sum = 1;
        long long current_run_max = 1;
        bool possible = true;
        
        current_f[1] = 1;
        
        for (int i = 2; i <= N; i++) {
            if (spf[i] == i) { // Prime
                if (std::abs(current_sum) <= width) {
                    // Random choice to explore solution space
                    if (rng() & 1) current_f[i] = 1;
                    else current_f[i] = -1;
                } else {
                    // Force correction if sum drifts too far
                    if (current_sum > 0) current_f[i] = -1;
                    else current_f[i] = 1;
                }
            } else {
                // Composite
                int p = spf[i];
                current_f[i] = current_f[p] * current_f[i/p];
            }
            
            current_sum += current_f[i];
            long long abs_s = std::abs(current_sum);
            if (abs_s > current_run_max) current_run_max = abs_s;
            
            // Pruning: If the current max prefix sum equals or exceeds the best found so far,
            // this run cannot produce a strictly better result (since max is monotonic over prefix).
            if (current_run_max >= best_max_abs) {
                possible = false;
                break;
            }
        }
        
        if (possible) {
            best_max_abs = current_run_max;
            for(int k = 1; k <= N; ++k) ans[k] = current_f[k];
            // If we find an extremely low max sum, we can stop early.
            if (best_max_abs <= 2) break;
        }
    }

    // Output the best sequence found
    for (int i = 1; i <= N; i++) {
        cout << ans[i] << (i == N ? "" : " ");
    }
    cout << "\n";

    return 0;
}