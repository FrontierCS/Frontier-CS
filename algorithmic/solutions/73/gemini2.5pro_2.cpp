#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int n;
std::vector<std::vector<int>> inv_parity;

// Safely gets inv_parity[l][r]. Returns 0 if l >= r, as an empty or single-element
// range has 0 inversions. This handles edge cases in the get_rel formula.
int safe_get(int l, int r) {
    if (l >= r) {
        return 0;
    }
    return inv_parity[l][r];
}

// Determines [p_i > p_j] mod 2 for i < j using precomputed query results.
// The formula is derived from the principle of inclusion-exclusion on inversion counts.
int get_rel(int i, int j) {
    return safe_get(i, j) ^ safe_get(i + 1, j) ^ safe_get(i, j - 1) ^ safe_get(i + 1, j - 1);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    if (n == 1) {
        std::cout << "1 1" << std::endl;
        return 0;
    }

    // Pre-computation phase: query all C(n, 2) subarrays.
    inv_parity.assign(n + 2, std::vector<int>(n + 2, 0));
    for (int l = 1; l <= n; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            std::cout << "0 " << l << " " << r << std::endl;
            std::cin >> inv_parity[l][r];
        }
    }

    std::vector<int> indices(n);
    std::iota(indices.begin(), indices.end(), 1);

    // Sort indices based on the values of the permutation at those indices.
    // The custom comparator uses get_rel to determine the relative order.
    std::stable_sort(indices.begin(), indices.end(), [&](int i, int j) {
        if (i == j) return false;
        
        // The comparison function must return true if p[i] < p[j].
        if (i < j) {
            // p[i] < p[j] is equivalent to [p[i] > p[j]] == 0
            return get_rel(i, j) == 0;
        } else { // i > j
            // p[i] < p[j] is equivalent to [p[j] > p[i]] == 1
            return get_rel(j, i) == 1;
        }
    });

    // Reconstruct the permutation from the sorted indices.
    // The index at rank k (0-indexed) corresponds to the position of value k+1.
    std::vector<int> p(n + 1);
    for (int i = 0; i < n; ++i) {
        p[indices[i]] = i + 1;
    }

    // Output the final answer.
    std::cout << "1 ";
    for (int i = 1; i <= n; ++i) {
        std::cout << p[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}