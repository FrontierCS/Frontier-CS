#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to compute GCD
long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

int main() {
    // Optimize I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long n;
    if (!(std::cin >> n)) return 0;

    // We will generate a sequence from the quadratic numbers i*(i+1)
    // and select a subsequence to satisfy the strictly increasing GCD condition.
    // Base sequence generator: val(i) = i * (i+1)
    
    std::vector<long long> result;
    
    // Start with the first two elements.
    // i=1 -> 2, i=2 -> 6. GCD(6, 2) = 2.
    // If n is very small, handle separately.
    if (n == 1) {
        std::cout << "1\n1\n";
        return 0;
    }
    
    // We maintain indices of the virtual quadratic sequence
    // idx represents the i for i*(i+1)
    
    // To save time, we generate values on the fly.
    // Current sequence
    result.push_back(2);
    if (6 > n) {
        // Only 2 fits? actually 1 fits better if n < 2 but n >= 1
        // If n < 6, we might have specific small cases.
        // For n=2: 1, 2. But we used 2.
        // Let's just output result scaled.
    } else {
        result.push_back(6);
    }
    
    long long current_gcd = 2; 
    long long last_idx = 2; // The index i for the last element added (val = i*(i+1))
    
    // We assume result has at least 2 elements if n >= 6.
    // If n < 6, the loop won't execute or logic handles it.
    
    // Greedy search for next elements
    while (true) {
        long long prev_val = result.back();
        bool found = false;
        
        // Search ahead for the next valid term
        // We limit search depth to avoid TLE if gaps become huge, 
        // though empirically gaps are small for this sequence.
        // We also must ensure val <= n.
        
        // Optimization: checking sequentially.
        // i*(i+1) grows quadratically. 
        // With n=10^12, i goes up to 10^6.
        // Max steps ~ 10^6. Inner loop runs small constant times on average.
        
        for (long long next_idx = last_idx + 1; ; ++next_idx) {
            long long next_val = next_idx * (next_idx + 1);
            if (next_val > n) {
                // Cannot find any more elements within range n
                goto finish;
            }
            
            long long g = gcd(next_val, prev_val);
            if (g > current_gcd) {
                result.push_back(next_val);
                current_gcd = g;
                last_idx = next_idx;
                found = true;
                break;
            }
            
            // Heuristic break to prevent too long search?
            // For the sequence i(i+1), valid successors are usually found quickly.
            // But let's verify constraint: if next_val gets too large relative to prev_val?
            // Actually, we just stop if next_val > n.
        }
        
        if (!found) break;
    }
    
    finish:;
    
    // Scaling step
    // We have a valid BSU: b_1, b_2, ... b_k.
    // We can multiply all by M = floor(n / b_k) to maximize the sum.
    // The conditions:
    // a_i = M * b_i
    // a_i > a_{i-1} <-> M * b_i > M * b_{i-1} (True since b_i strictly increasing and M >= 1)
    // gcd(a_i, a_{i-1}) = M * gcd(b_i, b_{i-1})
    // Condition: M * g_i > M * g_{i-1} <-> g_i > g_{i-1} (True by construction)
    
    if (result.empty()) {
        // Should not happen for n >= 2 given logic
        std::cout << "1\n1\n";
        return 0;
    }
    
    long long M = n / result.back();
    if (M < 1) M = 1; // Should be >= 1 since result.back() <= n
    
    std::cout << result.size() << "\n";
    for (size_t i = 0; i < result.size(); ++i) {
        std::cout << result[i] * M << (i == result.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}