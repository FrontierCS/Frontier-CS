#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

// Using global variables for simplicity in a competitive programming context
int n;
std::vector<int> p;
std::vector<int> p_idx;
std::vector<std::pair<int, int>> ops;

// Helper to perform an operation and record it
void perform_op(int x, int y) {
    if (x <= 0 || y <= 0 || x + y >= n) {
        // This indicates a logical error if it ever happens
        return;
    }
    ops.push_back({x, y});

    std::vector<int> prefix, middle, suffix;
    prefix.assign(p.begin(), p.begin() + x);
    middle.assign(p.begin() + x, p.begin() + n - y);
    suffix.assign(p.begin() + n - y, p.end());

    p.clear();
    p.insert(p.end(), suffix.begin(), suffix.end());
    p.insert(p.end(), middle.begin(), middle.end());
    p.insert(p.end(), prefix.begin(), prefix.end());

    for (int i = 0; i < n; ++i) {
        p_idx[p[i]] = i + 1;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    p.resize(n);
    p_idx.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        std::cin >> p[i];
        p_idx[p[i]] = i + 1;
    }

    if (n == 3) {
        // For n=3, the only operation is full reverse.
        // Target is the lexicographically smaller of p and reverse(p).
        std::vector<int> p_rev = p;
        std::reverse(p_rev.begin(), p_rev.end());
        if (p_rev < p) {
            perform_op(1, 1);
        }
    } else {
        // For n >= 4, we can sort the permutation completely.
        // Strategy: for i=1 to n, place number i at position i.
        for (int i = 1; i <= n; ++i) {
            int k = p_idx[i];
            if (k == i) {
                continue;
            }

            // Move element at k to position i, using position 1 as temporary
            // Step 1: Move element i from k to 1
            if (k > 1) {
                perform_op(k - 1, 1); // Moves p[k] to p[n]
                perform_op(n - 1, 1);   // Moves p[n] to p[1]
            }

            // Now i is at position 1
            // Step 2: Move element i from 1 to i
            if (i > 1) {
                perform_op(1, n - i);
                perform_op(i, 1);
            }
        }
    }

    std::cout << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}