#include <iostream>
#include <vector>
#include <algorithm>

// Finds the Longest Increasing or Decreasing Subsequence from the unused elements of p.
// Marks the elements of the found subsequence as used.
// is_lis: true for LIS, false for LDS.
std::vector<int> find_sequence(const std::vector<int>& p, std::vector<bool>& used, bool is_lis) {
    int n = p.size() - 1;
    
    // M_indices[k] stores the index in p of the last element of a subsequence of length k.
    // For LIS, this element has the smallest value.
    // For LDS, this element has the largest value.
    std::vector<int> M_indices(n + 2, 0); 
    std::vector<int> parent(n + 1, 0);
    int L = 0;

    for (int i = 1; i <= n; ++i) {
        if (used[i]) continue;

        // Binary search for the position to insert p[i]
        int lo = 1, hi = L, pos = 0;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            bool condition;
            if (is_lis) {
                condition = (p[M_indices[mid]] < p[i]);
            } else { // for LDS
                condition = (p[M_indices[mid]] > p[i]);
            }

            if (condition) {
                pos = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }

        int new_L = pos + 1;
        parent[i] = M_indices[new_L - 1];
        M_indices[new_L] = i;
        if (new_L > L) {
            L = new_L;
        }
    }

    if (L == 0) return {};

    std::vector<int> result;
    int current_idx = M_indices[L];
    while (current_idx != 0) {
        result.push_back(p[current_idx]);
        used[current_idx] = true;
        current_idx = parent[current_idx];
    }
    std::reverse(result.begin(), result.end());
    return result;
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        std::cin >> p[i];
    }
    
    std::vector<bool> used(n + 1, false);

    std::vector<int> a = find_sequence(p, used, true);
    std::vector<int> b = find_sequence(p, used, false);
    std::vector<int> c = find_sequence(p, used, true);
    
    std::vector<int> d;
    for (int i = 1; i <= n; ++i) {
        if (!used[i]) {
            d.push_back(p[i]);
        }
    }

    // Print lengths
    std::cout << a.size() << " " << b.size() << " " << c.size() << " " << d.size() << "\n";

    // Print subsequence a
    for (int i = 0; i < a.size(); ++i) {
        std::cout << a[i] << (i == a.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    // Print subsequence b
    for (int i = 0; i < b.size(); ++i) {
        std::cout << b[i] << (i == b.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    // Print subsequence c
    for (int i = 0; i < c.size(); ++i) {
        std::cout << c[i] << (i == c.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    // Print subsequence d
    for (int i = 0; i < d.size(); ++i) {
        std::cout << d[i] << (i == d.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}