#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <algorithm>

// Function to perform a query and return the result
long long perform_query(const std::vector<int>& indices) {
    if (indices.empty()) {
        return 0;
    }
    std::cout << "0 " << indices.size();
    for (int idx : indices) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    long long result;
    std::cin >> result;
    return result;
}

// Function to count '()' pairs in a list of pairs
// It relies on the triangular number property for a concatenated query string.
long long count_good_pairs(const std::vector<std::pair<int, int>>& pairs) {
    if (pairs.empty()) {
        return 0;
    }
    std::vector<int> indices;
    indices.reserve(pairs.size() * 2);
    for (const auto& p : pairs) {
        indices.push_back(p.first);
        indices.push_back(p.second);
    }
    long long f_val = perform_query(indices);
    if (f_val <= 0) {
        return 0;
    }
    // Invert the triangular number formula T(C) = C*(C+1)/2 to find C
    long long C = round((sqrt(1 + 8.0 * f_val) - 1.0) / 2.0);
    return C;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::string s(n, ' ');
    int open_ref = -1;

    // Phase 1: Find a reference character s_a = '('
    // We can find a pair (i, j) with s_i='(', s_j=')' in O(log(n^2)) queries
    
    std::vector<std::pair<int, int>> all_pairs;
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            all_pairs.push_back({i, j});
        }
    }

    int low = 0, high = all_pairs.size() - 1;
    int first_pair_idx = -1;

    // Binary search to find the first pair (i,j) which is '()'
    while (low < high) {
        int mid = low + (high - low) / 2;
        std::vector<std::pair<int, int>> sub_pairs(all_pairs.begin(), all_pairs.begin() + mid + 1);
        if (count_good_pairs(sub_pairs) > 0) {
            high = mid;
        } else {
            low = mid + 1;
        }
    }
    
    // Fallback in case the above BS logic has issues with interacting pairs
    long long total_pairs_count = count_good_pairs(all_pairs);
    while (count_good_pairs({all_pairs[low]}) == 0) {
        std::vector<std::pair<int, int>> current_prefix(all_pairs.begin(), all_pairs.begin() + low + 1);
        long long prefix_count = count_good_pairs(current_prefix);
        low++;
        std::vector<std::pair<int, int>> next_prefix(all_pairs.begin(), all_pairs.begin() + low + 1);
        long long next_prefix_count = count_good_pairs(next_prefix);
        if (next_prefix_count > prefix_count) {
            break;
        }
    }

    std::pair<int, int> ref_pair = all_pairs[low];
    open_ref = ref_pair.first;
    s[ref_pair.first - 1] = '(';
    s[ref_pair.second - 1] = ')';

    // Phase 2: Determine remaining characters
    for (int i = 1; i <= n; ++i) {
        if (s[i - 1] == ' ') {
            if (perform_query({open_ref, i}) == 1) {
                s[i - 1] = ')';
            } else {
                s[i - 1] = '(';
            }
        }
    }

    std::cout << "1 " << s << std::endl;

    return 0;
}