#include <iostream>
#include <vector>
#include <algorithm>
#include <utility>

// Function to find the Longest Increasing/Decreasing Subsequence.
// Input: a vector of pairs, where each pair is {value, original_index}.
// is_lds: if true, finds Longest Decreasing Subsequence, otherwise Longest Increasing.
// Returns a vector of original indices that form the subsequence.
std::vector<int> find_subsequence(const std::vector<std::pair<int, int>>& p, bool is_lds) {
    if (p.empty()) {
        return {};
    }

    std::vector<std::pair<int, int>> temp_p = p;
    if (is_lds) {
        for (auto& pair : temp_p) {
            pair.first = -pair.first;
        }
    }

    int n = temp_p.size();
    if (n == 0) return {};
    
    std::vector<int> M(n + 1, -1);
    std::vector<int> pred(n, -1);
    int L = 0;

    for (int i = 0; i < n; ++i) {
        int lo = 1, hi = L;
        int pos = 0; // The length of LIS we can extend
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (temp_p[M[mid]].first < temp_p[i].first) {
                pos = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        
        int newL = pos + 1;
        if (pos > 0) {
            pred[i] = M[pos];
        }
        M[newL] = i;
        if (newL > L) {
            L = newL;
        }
    }

    std::vector<int> result;
    if (L > 0) {
        int k = M[L];
        while (k != -1) {
            result.push_back(temp_p[k].second);
            k = pred[k];
        }
    }
    std::reverse(result.begin(), result.end());
    return result;
}

// Helper function to print a subsequence given its indices and the original permutation.
void print_subsequence(const std::vector<int>& indices, const std::vector<int>& p_orig) {
    std::vector<int> sorted_indices = indices;
    std::sort(sorted_indices.begin(), sorted_indices.end());
    
    std::cout << sorted_indices.size();
    for (int idx : sorted_indices) {
        std::cout << " " << p_orig[idx];
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    std::vector<int> p_orig(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> p_orig[i];
    }

    std::vector<bool> used(n, false);
    std::vector<int> a_idx, b_idx, c_idx, d_idx;

    // Step 1: Find LIS for subsequence 'a' from the whole permutation
    std::vector<std::pair<int, int>> p_cur;
    for (int i = 0; i < n; ++i) {
        p_cur.push_back({p_orig[i], i});
    }
    a_idx = find_subsequence(p_cur, false);
    for (int idx : a_idx) {
        used[idx] = true;
    }

    // Step 2: Find LDS for subsequence 'b' from the remaining elements
    p_cur.clear();
    for (int i = 0; i < n; ++i) {
        if (!used[i]) {
            p_cur.push_back({p_orig[i], i});
        }
    }
    b_idx = find_subsequence(p_cur, true);
    for (int idx : b_idx) {
        used[idx] = true;
    }

    // Step 3: Find LIS for subsequence 'c' from the remaining elements
    p_cur.clear();
    for (int i = 0; i < n; ++i) {
        if (!used[i]) {
            p_cur.push_back({p_orig[i], i});
        }
    }
    c_idx = find_subsequence(p_cur, false);
    for (int idx : c_idx) {
        used[idx] = true;
    }

    // Step 4: Subsequence 'd' consists of all other remaining elements
    for (int i = 0; i < n; ++i) {
        if (!used[i]) {
            d_idx.push_back(i);
        }
    }
    
    // Output the lengths of the four subsequences
    std::cout << a_idx.size() << " " << b_idx.size() << " " << c_idx.size() << " " << d_idx.size() << "\n";

    // Output the subsequences themselves
    print_subsequence(a_idx, p_orig);
    print_subsequence(b_idx, p_orig);
    print_subsequence(c_idx, p_orig);
    print_subsequence(d_idx, p_orig);

    return 0;
}