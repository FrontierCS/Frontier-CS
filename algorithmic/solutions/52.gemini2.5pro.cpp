#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Using std::endl is generally sufficient for flushing in competitive programming
// when followed by a read from std::cin, as it is tied to the input stream.

/**
 * @brief Asks for the number of value-contiguous segments in p[l...r].
 * @param l The left boundary of the interval (1-indexed).
 * @param r The right boundary of the interval (1-indexed).
 * @return The number of value-contiguous segments.
 */
int ask(int l, int r) {
    std::cout << "1 " << l << " " << r << std::endl;
    int res;
    std::cin >> res;
    return res;
}

/**
 * @brief Swaps elements at positions i and j in the hidden permutation.
 * @param i A position to swap (1-indexed).
 * @param j Another position to swap (1-indexed).
 */
void swap_elements(int i, int j) {
    if (i == j) return;
    std::cout << "2 " << i << " " << j << std::endl;
    int res;
    std::cin >> res;
}

/**
 * @brief Submits the final determined permutation.
 * @param n The length of the permutation.
 * @param p The permutation (1-indexed).
 */
void answer(int n, const std::vector<int>& p) {
    std::cout << "3";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    long long l1, l2;
    std::cin >> n >> l1 >> l2;

    if (n == 1) {
        std::vector<int> p = {0, 1};
        answer(n, p);
        return 0;
    }

    std::vector<int> pos(n + 1);
    std::iota(pos.begin(), pos.end(), 0);

    // Phase 1: Caterpillar Construction
    for (int i = 1; i < n; ++i) {
        // Binary search for the element that extends the value-contiguous prefix p[1...i]
        int low = i + 1, high = n, extender_pos = n;
        
        while(low <= high) {
            int mid = low + (high - low) / 2;
            int q_sub = ask(i + 1, mid);
            int q_total = ask(1, mid);
            // Number of extenders in p[i+1...mid] for p[1...i]
            int ext_count = 1 + q_sub - q_total;
            if (ext_count > 0) {
                extender_pos = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        
        swap_elements(i + 1, extender_pos);
        std::swap(pos[i + 1], pos[extender_pos]);
    }

    // Phase 2: Value Determination
    std::vector<int> p_val(n + 1);
    // Arbitrarily fix the first two relative values.
    // The other possibility would lead to the n+1-p permutation.
    p_val[1] = 1;
    p_val[2] = 2;
    int minv = 1, maxv = 2;

    for (int i = 2; i < n; ++i) {
        int q = ask(2, i + 1);
        bool is_p1_min = (p_val[1] == minv);
        bool is_contiguous = (q == 1);

        if ((is_p1_min && is_contiguous) || (!is_p1_min && !is_contiguous)) {
            // Extend on the max side
            p_val[i + 1] = ++maxv;
        } else {
            // Extend on the min side
            p_val[i + 1] = --minv;
        }
    }

    // Map relative values to the range [1, n] and assign to original positions
    std::vector<int> ans(n + 1);
    for (int i = 1; i <= n; ++i) {
        ans[pos[i]] = p_val[i] - minv + 1;
    }

    answer(n, ans);

    return 0;
}