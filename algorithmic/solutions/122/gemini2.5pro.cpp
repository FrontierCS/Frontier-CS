#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>
#include <algorithm>
#include <string>

// Function to print a query with n repeated values of val
void print_query(int n, int val) {
    std::cout << "? " << n;
    for (int i = 0; i < n; ++i) {
        std::cout << " " << val;
    }
    std::cout << std::endl;
}

void solve() {
    // Query 1: A large number of words of length 1 to get a coarse range for W.
    const int n1 = 100000;
    print_query(n1, 1);

    long long L1;
    std::cin >> L1;
    if (L1 == -1) exit(0);

    if (L1 == 1) {
        // ceil(100000/W) = 1  => 0 < 100000/W <= 1 => W >= 100000.
        // Since W is at most 100000, W must be 100000.
        std::cout << "! 100000" << std::endl;
        return;
    }

    // From L1 = ceil(n1/W), we have L1-1 < n1/W <= L1.
    // This gives n1/L1 <= W < n1/(L1-1).
    long long W_min = static_cast<long long>(ceil(static_cast<double>(n1) / L1));
    long long W_max = static_cast<long long>(floor(static_cast<double>(n1 - 1) / (L1 - 1)));
    W_max = std::min(W_max, 100000LL);

    // Query 2: Words of a different length to get a second constraint.
    int k2 = 401; // A heuristic choice (prime, not too small)
    int n2 = 401;

    if (k2 > W_min) {
        // If the range of W is small, k2 must be smaller than W_min to be valid.
        k2 = std::max(1LL, W_min / 2);
    }
    
    print_query(n2, k2);

    long long L2;
    std::cin >> L2;
    if (L2 == -1) exit(0);
    
    // If the second query returns 0, it means W < k2. This gives a strong upper bound.
    if (L2 == 0) {
        W_max = std::min(W_max, (long long)k2 - 1);
    }

    // Iterate through the candidate range and find the unique W satisfying both query responses.
    for (long long W = W_min; W <= W_max; ++W) {
        if (static_cast<long long>(ceil(static_cast<double>(n1) / W)) == L1) {
            
            if (k2 > W) { // This W cannot fit a word of length k2
                if (L2 == 0) { // This is consistent with a 0 response
                    std::cout << "! " << W << std::endl;
                    return;
                }
                continue;
            }

            long long p = W / k2;
            if (p == 0) continue; // Should have been caught by k2 > W
            
            long long l2_cand = static_cast<long long>(ceil(static_cast<double>(n2) / p));
            if (l2_cand == L2) {
                std::cout << "! " << W << std::endl;
                return;
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}