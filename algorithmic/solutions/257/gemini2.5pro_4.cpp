#include <iostream>
#include <vector>
#include <stack>
#include <utility>

std::vector<int> ans;

// Function to perform a query and get mode and frequency
std::pair<int, int> query(int l, int r) {
    std::cout << "? " << l << " " << r << std::endl;
    int x, f;
    std::cin >> x >> f;
    return {x, f};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    ans.resize(n + 1);

    // Use a stack for an iterative version of the recursive divide-and-conquer
    std::stack<std::pair<int, int>> ranges;
    ranges.push({1, n});

    while (!ranges.empty()) {
        auto [l, r] = ranges.top();
        ranges.pop();

        if (l > r) {
            continue;
        }

        auto [x, f] = query(l, r);
        int len = r - l + 1;

        // Optimization: if the whole range is the mode, fill and continue
        if (f == len) {
            for (int i = l; i <= r; ++i) {
                ans[i] = x;
            }
            continue;
        }
        
        // Binary search for the starting position of the mode's block.
        // We look for the largest `p` such that `query(p, r)` returns `(x, f)`.
        // This `p` will be the starting position of the block.
        int pos = l;
        int low = l + 1, high = r - f + 1;

        while (low <= high) {
            int mid = low + (high - low) / 2;
            auto [xq, fq] = query(mid, r);
            if (xq == x && fq == f) {
                pos = mid;
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }

        // Fill the determined block in the answer array
        for (int i = 0; i < f; ++i) {
            ans[pos + i] = x;
        }
        
        // Push the remaining sub-ranges to the stack to be solved
        if (l <= pos - 1) {
            ranges.push({l, pos - 1});
        }
        if (pos + f <= r) {
            ranges.push({pos + f, r});
        }
    }

    // Output the final reconstructed array
    std::cout << "! ";
    for (int i = 1; i <= n; ++i) {
        std::cout << ans[i] << (i == n ? "" : " ");
    }
    std::cout << std::endl;

    return 0;
}