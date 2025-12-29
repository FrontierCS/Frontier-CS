#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a query and read the result.
// It's good practice to have this helper for interactive problems.
int query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int result;
    std::cin >> result;
    // On receiving -1, it means an error occurred (e.g., invalid query or query limit exceeded).
    // The program should terminate immediately.
    if (result == -1) {
        exit(0);
    }
    return result;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n + 1);
    std::vector<int> or_w_1(n + 1);

    // Step 1: Query p[1] with all other elements
    for (int i = 2; i <= n; ++i) {
        or_w_1[i] = query(1, i);
    }

    // Step 2: Determine p[1].
    // p[1] = (p[1]|p[2]) & (p[1]|p[3]) & ... & (p[1]|p[n])
    // This works because for n>=3, the bitwise AND of all numbers in {0..n-1} except any one value is 0.
    int p1_val = -1; // Represents all bits set
    for (int i = 2; i <= n; ++i) {
        if (p1_val == -1) {
            p1_val = or_w_1[i];
        } else {
            p1_val &= or_w_1[i];
        }
    }
    p[1] = p1_val;

    // Step 3: Determine p[2]...p[n].
    // For each i > 1, we know p[1] and p[1]|p[i].
    // Since p is a permutation of {0..n-1}, we can uniquely determine p[i].
    // A simple method that works is to recognize that one of p[j] must be 0.
    // If p[k] = 0, then p[1]|p[k] = p[1]. The set {p[1]|p[i] for i=2..n} will contain p[1].
    // The set {p[1], p[1]|p[2], ..., p[1]|p[n]} is in fact the set {p[1], ..., p[n]},
    // because for each p[i], there is a query result p[1]|p[i], and for p[1],
    // there is a p[k]=0, so p[1]|p[k]=p[1].
    // So the values of p[2] to p[n] are simply the results of the OR queries with p[1].
    for (int i = 2; i <= n; ++i) {
        p[i] = or_w_1[i];
    }
    
    // Output the final answer
    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}