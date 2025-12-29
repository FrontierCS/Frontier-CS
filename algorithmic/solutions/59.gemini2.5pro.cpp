#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <list>

// Wrapper for queries to the interactor.
char query(int i, int j) {
    std::cout << "? " << i << " " << j << std::endl;
    char response;
    std::cin >> response;
    if (response == '!' || response == '?') {
        // This should not happen if the logic is correct.
        // It's a safeguard against unexpected interactor behavior.
        exit(0);
    }
    return response;
}

// A map to memoize query results to avoid asking the same question twice.
// The key is a unique integer for an unordered pair (i, j).
std::map<long long, char> memo;

// A memoized query function. It stores results in a canonical way (i < j).
char memoized_query(int i, int j) {
    if (i == j) return '='; // Should not happen with 1-based indexing and i!=j
    if (i > j) {
        char res = memoized_query(j, i);
        return res == '<' ? '>' : '<';
    }
    long long key = (long long)i * 30001 + j;
    if (memo.count(key)) {
        return memo[key];
    }
    char res = query(i, j);
    memo[key] = res;
    return res;
}

// Custom comparator for sorting indices based on their values in the secret array.
bool compare_indices(int i, int j) {
    return memoized_query(i, j) == '<';
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n + 1, 0);
    std::list<int> unknown_vals;
    for (int i = 1; i <= n; ++i) {
        unknown_vals.push_back(i);
    }

    // Process indices in blocks of 3.
    for (int i = 1; i <= n; i += 3) {
        int remaining_count = n - i + 1;
        if (remaining_count == 0) break;

        // The indices we need to determine in this block.
        std::vector<int> block_indices;
        if (remaining_count >= 3) {
            block_indices = {i, i + 1, i + 2};
        } else if (remaining_count == 2) {
            block_indices = {i, i + 1};
        } else {
            block_indices = {i};
        }

        // Determine the size of the group to sort. For a block of 3, we consider
        // a group of 5 elements (3 from the block + 2 helpers).
        // For tails, the group size is simply the number of remaining elements.
        int group_size;
        if (remaining_count >= 5) {
            group_size = 5;
        } else {
            group_size = remaining_count;
        }

        std::vector<int> current_indices;
        for (int j = 0; j < group_size; ++j) {
            current_indices.push_back(i + j);
        }

        // The candidate values for this group are the smallest `group_size`
        // values that have not yet been assigned to a position.
        std::vector<int> cands;
        auto it = unknown_vals.begin();
        for (int j = 0; j < group_size; ++j) {
            cands.push_back(*it);
            it++;
        }

        // Sort the indices in the current group based on their values.
        std::sort(current_indices.begin(), current_indices.end(), compare_indices);

        // Map the sorted indices to the sorted candidate values.
        std::map<int, int> val_map;
        for (int j = 0; j < group_size; ++j) {
            val_map[current_indices[j]] = cands[j];
        }

        // Assign the determined values to the final permutation `p`
        // and remove them from the list of unknown values.
        for (int idx : block_indices) {
            p[idx] = val_map[idx];
            unknown_vals.remove(p[idx]);
        }
    }

    // Output the final permutation.
    std::cout << "! ";
    for (int i = 1; i <= n; ++i) {
        std::cout << p[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}