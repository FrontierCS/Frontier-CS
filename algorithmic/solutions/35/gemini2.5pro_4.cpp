#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>

// Function to ask a query to the interactor.
// It takes a value `x` and a set of indices `s`.
// It returns true if the value `x` is present at any of the indices in `s`.
bool ask(int x, const std::vector<int>& s) {
    if (s.empty()) {
        return false;
    }
    std::cout << "? " << x << " " << s.size();
    for (int idx : s) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response == 1;
}

// Function to find the first occurrence of a value `x` within a sorted list of `indices`.
// It uses binary search on the indices to find the position.
// Returns the index if found, otherwise -1.
int find_pos(int x, const std::vector<int>& indices) {
    if (indices.empty()) {
        return -1;
    }
    int low = 0, high = indices.size() - 1;
    int ans_idx = -1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        std::vector<int> query_indices;
        for (int i = low; i <= mid; ++i) {
            query_indices.push_back(indices[i]);
        }
        if (ask(x, query_indices)) {
            ans_idx = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    return (ans_idx == -1) ? -1 : indices[ans_idx];
}

// The main logic to solve a single test case.
void solve() {
    int n;
    std::cin >> n;
    if (n == -1) {
        exit(0);
    }

    int total_len = 2 * n - 1;
    std::vector<bool> is_paired(total_len + 1, false);

    // Iterate through each number from 1 to n to find its positions.
    for (int x = 1; x <= n; ++x) {
        // Collect all indices that are not yet part of a pair.
        std::vector<int> unpaired_now;
        for (int i = 1; i <= total_len; ++i) {
            if (!is_paired[i]) {
                unpaired_now.push_back(i);
            }
        }

        // Find the first position of x among the unpaired indices.
        int pos1 = find_pos(x, unpaired_now);
        
        // If x is not found, it cannot be the unique number, so we can skip.
        // In this problem, every number is present at least once.
        if (pos1 == -1) continue;
        
        is_paired[pos1] = true;

        // Re-collect unpaired indices after marking pos1.
        unpaired_now.clear();
        for (int i = 1; i <= total_len; ++i) {
            if (!is_paired[i]) {
                unpaired_now.push_back(i);
            }
        }

        // Try to find a second position for x.
        int pos2 = find_pos(x, unpaired_now);

        if (pos2 == -1) {
            // If a second position is not found, x must be the unique number.
            std::cout << "! " << x << std::endl;
            return;
        }
        is_paired[pos2] = true;
    }
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}