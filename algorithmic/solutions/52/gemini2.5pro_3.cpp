#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a swap operation via interaction.
void do_swap(int i, int j) {
    if (i == j) return;
    std::cout << "2 " << i << " " << j << std::endl;
    int dummy;
    std::cin >> dummy;
}

// Function to perform a query operation via interaction.
int do_ask(int l, int r) {
    std::cout << "1 " << l << " " << r << std::endl;
    int res;
    std::cin >> res;
    return res;
}

// Function to output the final answer.
void do_answer(const std::vector<int>& p) {
    std::cout << "3";
    for (size_t i = 1; i < p.size(); ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, l1, l2;
    std::cin >> n >> l1 >> l2;

    // `pos[i]` stores the original index of the element currently at position `i`.
    // Initially, the element at position `i` is the one that started at index `i`.
    std::vector<int> pos(n + 1);
    std::iota(pos.begin(), pos.end(), 0);

    // The core strategy is to build a chain of value-adjacent elements one by one.
    // We place the elements of this chain at positions 1, 2, 3, ...
    // At step `i`, we have a chain of `i` elements at positions 1 to `i`.
    // We then find a value-neighbor of the element at position `i` from the
    // remaining elements (at positions `i+1` to `n`) and move it to position `i+1`.
    for (int i = 1; i < n; ++i) {
        // The element at position `i` is our current pivot. We search for its neighbor.
        // The search space for the neighbor is positions `i+1` through `n`.
        for (int j = i + 1; j <= n; ++j) {
            // Bring the element from position `j` to position `i+1` to test it.
            do_swap(i + 1, j);
            std::swap(pos[i + 1], pos[j]);

            // A query on `[i, i+1]` can tell us if `p[i]` and `p[i+1]` have adjacent values.
            // `ask(i, i+1)` returns the number of value-contiguous subsegments in `p[i..i+1]`.
            // These are `[p[i]]`, `[p[i+1]]`, and potentially `[p[i], p[i+1]]`.
            // So, `ask(i, i+1)` is 3 if `p[i]` and `p[i+1]` are value-adjacent, and 2 otherwise.
            if (do_ask(i, i + 1) == 3) {
                // We found a neighbor. It's now at position `i+1`. We leave it there
                // and proceed to extend the chain from this new element.
                break;
            }

            // If it's not a neighbor, we swap back to restore the original state of this step
            // to correctly test the next candidate from its original position.
            do_swap(i + 1, j);
            std::swap(pos[i + 1], pos[j]);
        }
    }

    // After the loops, the elements at positions 1, 2, ..., n form a chain
    // of value-adjacent numbers. This means their original values form a
    // monotonic sequence of consecutive integers. Since it's a permutation of 1 to n,
    // this sequence must be either (1, 2, ..., n) or (n, n-1, ..., 1).
    // Let's assume one of these, say (1, 2, ..., n).
    // The element originally at `pos[i]` is now at position `i`, so we assign it value `i`.
    std::vector<int> ans(n + 1);
    for (int i = 1; i <= n; ++i) {
        ans[pos[i]] = i;
    }
    
    // The problem statement guarantees that `p` and `n+1-p` are indistinguishable.
    // Our constructed answer is one of these two possibilities.
    do_answer(ans);

    return 0;
}