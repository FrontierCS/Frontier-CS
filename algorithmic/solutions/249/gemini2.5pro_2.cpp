#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a query
int query(int i, int j) {
    std::cout << "? " << i + 1 << " " << j + 1 << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to print the final answer
void answer(const std::vector<int>& p) {
    std::cout << "! ";
    for (size_t i = 0; i < p.size(); ++i) {
        std::cout << p[i] << (i == p.size() - 1 ? "" : " ");
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    if (n == 0) {
        std::cout << "!" << std::endl;
        return 0;
    }

    std::vector<int> p(n);
    
    // Step 1: Fix an anchor and find its best partner for a minimal OR.
    // This partner is our candidate for the index of 0.
    int anchor_idx = 0;
    int zero_cand_idx = 1;
    
    int min_or_val = query(anchor_idx, zero_cand_idx);

    for (int i = 2; i < n; ++i) {
        int current_or = query(anchor_idx, i);
        if (current_or < min_or_val) {
            min_or_val = current_or;
            zero_cand_idx = i;
        }
    }

    // Now, we have a strong hypothesis: p[zero_cand_idx] = 0 and p[anchor_idx] = min_or_val.
    // The only other possibility is that p[anchor_idx] = 0 and p[zero_cand_idx] = min_or_val.
    // We can distinguish these with one more element.
    
    int zero_idx;
    int val_cand = min_or_val;

    // Pick a test index different from anchor_idx and zero_cand_idx
    int test_idx = 0;
    while (test_idx == anchor_idx || test_idx == zero_cand_idx) {
        test_idx++;
    }

    int or_zero_cand_test = query(zero_cand_idx, test_idx);
    int or_anchor_test = query(anchor_idx, test_idx);

    // Hypothesis: p[zero_cand_idx] = 0 and p[anchor_idx] = val_cand.
    // If true, then p[test_idx] = or_zero_cand_test.
    // And p[anchor_idx] | p[test_idx] must be or_anchor_test.
    // Let's check: (val_cand | or_zero_cand_test) == or_anchor_test
    
    if ((val_cand | or_zero_cand_test) == or_anchor_test) {
        // Hypothesis is correct
        zero_idx = zero_cand_idx;
    } else {
        // Hypothesis is wrong, so the roles are swapped
        zero_idx = anchor_idx;
    }
    
    // Step 3: Find the full permutation using the index of 0.
    p[zero_idx] = 0;
    for (int i = 0; i < n; ++i) {
        if (i == zero_idx) continue;
        p[i] = query(zero_idx, i);
    }
    
    answer(p);

    return 0;
}