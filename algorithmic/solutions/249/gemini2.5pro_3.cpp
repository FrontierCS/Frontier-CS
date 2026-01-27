#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to perform a query using 1-based indexing
int ask(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    int result;
    std::cin >> result;
    return result;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // We will use 0-based indexing for our arrays `p`, `q1`, `q2`.
    std::vector<int> p(n);
    std::vector<int> q1(n);
    std::vector<int> q2(n);

    // Get all ORs with the first element (index 0).
    // q1[i] will store p[0] | p[i].
    for (int i = 1; i < n; ++i) {
        q1[i] = ask(1, i + 1);
    }

    // Get all ORs with the second element (index 1).
    // q2[i] will store p[1] | p[i].
    for (int i = 2; i < n; ++i) {
        q2[i] = ask(2, i + 1);
    }

    // We have p[0]|p[1] from the first loop (q1[1]).
    int q12 = q1[1];

    // Determine p[0] using the identity p[i] = &_{j!=i} (p[i]|p[j]).
    int all_bits_mask = (1 << 12) - 1; // n <= 2048, so values are < 2048 (< 2^11). 12 bits are safe.
    p[0] = all_bits_mask;
    for (int i = 1; i < n; ++i) {
        p[0] &= q1[i];
    }
    
    // Determine p[1] similarly.
    p[1] = q12;
    for (int i = 2; i < n; ++i) {
        p[1] &= q2[i];
    }

    // Determine the rest of the permutation.
    int mask = p[0] & p[1];
    int inv_mask = ~mask;

    std::vector<bool> used(n, false);
    used[p[0]] = true;
    used[p[1]] = true;
    
    std::vector<int> p_known_part(n);

    // For each remaining element p[i], calculate its known part.
    // The known part consists of bits where at least one of p[0] or p[1] has a 0.
    for (int i = 2; i < n; ++i) {
        int p_i_known_from_1 = q1[i] & (~p[0]);
        int p_i_known_from_2 = q2[i] & (~p[1]);
        p_known_part[i] = p_i_known_from_1 | p_i_known_from_2;
    }

    // Create a map from the known part of a value to the value itself.
    // This relies on the fact that for the unused values, this mapping is unique.
    std::map<int, int> known_part_to_val;
    for (int v = 0; v < n; ++v) {
        if (!used[v]) {
            known_part_to_val[v & inv_mask] = v;
        }
    }

    // Use the map to find the full value for each remaining element.
    for (int i = 2; i < n; ++i) {
        p[i] = known_part_to_val[p_known_part[i]];
    }

    // Print the final answer.
    std::cout << "! ";
    for (int i = 0; i < n; ++i) {
        std::cout << p[i] << (i == n - 1 ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}