#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Define maximum N as per constraints. 10^6 is the limit.
const int MAXN = 1000005;

// spf[i] stores the smallest prime factor of i.
int spf[MAXN];
// f[i] stores the value of the multiplicative function at i.
int f[MAXN];
// List of primes up to n.
vector<int> primes;

// Sieve of Eratosthenes to precompute smallest prime factors.
// Runs in O(n) time.
void sieve(int n) {
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
}

int main() {
    // optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;
    
    // Precompute prime factors
    sieve(n);
    
    // f(1) is always 1 for a completely multiplicative function with values {-1, 1}
    // because f(1) = f(1*1) = f(1)*f(1) => f(1)=1.
    f[1] = 1;
    long long current_sum = 1; 
    
    // Iterate through each prime.
    // We decide f(p) when we reach p.
    // The numbers between p and next_prime (exclusive) are composites whose prime factors are <= p.
    // However, since next_prime < 2*p (by Bertrand's postulate), numbers k in (p, next_prime)
    // cannot be multiples of p (except if k >= 2p).
    // Thus, for all k in (p, next_prime), k is not divisible by p.
    // Their values f(k) are therefore determined entirely by f values of primes < p.
    // This allows us to calculate their contribution before deciding f(p).
    
    for (size_t i = 0; i < primes.size(); ++i) {
        int p = primes[i];
        // The interval of numbers to consider is [p, next_p - 1]
        // If p is the last prime, interval is [p, n]
        int limit = (i + 1 < primes.size()) ? primes[i+1] - 1 : n;
        
        // We will calculate the contribution of the composite numbers in the gap (p, limit]
        // These values are fixed and do not depend on f(p).
        
        long long comp_sum = 0;
        long long max_comp_prefix = 0; // max positive relative prefix sum
        long long min_comp_prefix = 0; // min negative relative prefix sum
        
        for (int k = p + 1; k <= limit; ++k) {
            int sp = spf[k];
            // Since k is composite and k < 2p, all prime factors are < p.
            // f values for factors are already computed.
            f[k] = f[sp] * f[k / sp];
            
            comp_sum += f[k];
            if (comp_sum > max_comp_prefix) max_comp_prefix = comp_sum;
            if (comp_sum < min_comp_prefix) min_comp_prefix = comp_sum;
        }
        
        // Now we choose f(p) to minimize the maximum absolute prefix sum in the range [p, limit].
        // The prefix sums in this range will be:
        // S_k = S_{p-1} + f(p) + (sum_{j=p+1}^k f(j))
        // Let Base = S_{p-1} + f(p). The values relative to Base are the composite prefix sums.
        
        // Option 1: Choose f(p) = 1
        long long s1 = current_sum + 1;
        // Peak magnitude in the interval
        long long peak1 = max(abs(s1 + max_comp_prefix), abs(s1 + min_comp_prefix));
        // Final sum after the interval
        long long final1 = abs(s1 + comp_sum);
        
        // Option 2: Choose f(p) = -1
        long long s2 = current_sum - 1;
        long long peak2 = max(abs(s2 + max_comp_prefix), abs(s2 + min_comp_prefix));
        long long final2 = abs(s2 + comp_sum);
        
        int choice = 1;
        // Greedy strategy: minimize peak in the interval. 
        // Break ties by minimizing the absolute value of the final sum.
        if (peak2 < peak1) {
            choice = -1;
        } else if (peak2 == peak1) {
            if (final2 < final1) {
                choice = -1;
            }
        }
        
        f[p] = choice;
        // Update current_sum to be S_{limit}
        current_sum += choice + comp_sum;
    }
    
    // Output the results
    for (int i = 1; i <= n; ++i) {
        cout << f[i] << (i == n ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}