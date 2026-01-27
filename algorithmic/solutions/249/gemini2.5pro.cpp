#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a query
int query(int i, int j) {
    std::cout << "? " << i + 1 << " " << j + 1 << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) exit(0); // Exit on error
    return result;
}

// Function to print the final answer
void answer(const std::vector<int>& p) {
    std::cout << "!";
    for (int val : p) {
        std::cout << " " << val;
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n);
    int pivot_idx = 0;
    
    std::vector<int> or_with_pivot(n);
    int min_or_val = (1 << 12); // n <= 2048, values are < n
    int min_or_idx = -1;

    for (int i = 1; i < n; ++i) {
        or_with_pivot[i] = query(pivot_idx, i);
        if (or_with_pivot[i] < min_or_val) {
            min_or_val = or_with_pivot[i];
            min_or_idx = i;
        }
    }

    // Two candidates for the position of 0: pivot_idx and min_or_idx.
    
    // Pick a verification index `check_idx`, different from pivot_idx and min_or_idx.
    int check_idx = 1;
    if (n > 2) { // For n=2 this problem is not defined, n>=3
      if (check_idx == min_or_idx) {
          check_idx = 2;
      }
    }
    
    int or_check_min_or = query(check_idx, min_or_idx);

    // Hypothesis: p[min_or_idx] is 0.
    // If true, p[pivot_idx] = min_or_val and p[check_idx] = or_check_min_or.
    // Check for consistency: (p[pivot_idx] | p[check_idx]) should equal or_with_pivot[check_idx].
    if ((min_or_val | or_check_min_or) == or_with_pivot[check_idx]) {
        // Hypothesis 1 is correct. p[min_or_idx] = 0.
        p[min_or_idx] = 0;
        p[pivot_idx] = min_or_val;
        // We already know p[check_idx] from the test query
        p[check_idx] = or_check_min_or;
        // Find the rest of the permutation
        for (int i = 1; i < n; ++i) {
            if (i != min_or_idx && i != check_idx) {
                p[i] = query(i, min_or_idx);
            }
        }
    } else {
        // Hypothesis 2 is correct. p[pivot_idx] = 0.
        p[pivot_idx] = 0;
        for (int i = 1; i < n; ++i) {
            p[i] = or_with_pivot[i];
        }
    }

    answer(p);

    return 0;
}