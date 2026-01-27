#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <tuple>

// This struct is used to store the added edges for the final output.
// The format is (u, c, v), representing adding edge u->v because
// edges u->c and c->v exist.
std::vector<std::tuple<int, int, int>> added_edges;

/**
 * @brief Adds edges for a jump of a specific length.
 *
 * For a given jump length `len`, this function adds an edge `i -> i+len` for all
 * possible start vertices `i`. The justification for adding `i -> i+len` is an
 * existing path `i -> i+prev_len1 -> i+len`. The second hop in this path,
 * `i+prev_len1 -> i+len`, must have a length of `prev_len2 = len - prev_len1`.
 *
 * @param len The length of the jump to add.
 * @param n The maximum vertex index in the graph.
 * @param prev_len1 The length of the first jump in the path of length 2.
 * @param prev_len2 The length of the second jump in the path of length 2.
 */
void add_jump_edges(int len, int n, int prev_len1, int prev_len2) {
    if (len > n) return;
    for (int i = 0; i <= n - len; ++i) {
        added_edges.emplace_back(i, i + prev_len1, i + len);
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n <= 1) {
        std::cout << 0 << std::endl;
        return 0;
    }
    
    // Choose k optimally to minimize the number of edges.
    // The number of edges is roughly proportional to (2k + n/k^2).
    // This expression is minimized when k is around n^(1/3).
    int k = 1;
    if (n > 0) {
      k = round(pow(n, 1.0/3.0));
    }
    if (k <= 1 && n > 1) k = 2; // k must be at least 2 for the strategy to work.

    // Phase 1: Generate jumps {2, ..., k-1}.
    // Each jump of length `i` is created from `i-1` and `1`.
    for (int i = 2; i < k; ++i) {
        add_jump_edges(i, n, i - 1, 1);
    }

    // Phase 2: Generate jumps {k, 2k, ..., (k-1)k}.
    // First, generate jump `k` from `k-1` and `1`.
    if (k <= n) {
      add_jump_edges(k, n, k - 1, 1);
    }
    // Then, generate `i*k` from `(i-1)*k` and `k`.
    for (int i = 2; i < k; ++i) {
        add_jump_edges(i * k, n, (i - 1) * k, k);
    }
    
    // Phase 3: Generate jumps {k^2, 2k^2, ..., A*k^2} where A=floor(n/k^2).
    int k2 = k * k;
    if (k2 <= n) {
        // First, generate jump `k^2` from `(k-1)*k` and `k`.
        add_jump_edges(k2, n, (k - 1) * k, k);
    }

    int A = n / k2;
    // Then, generate `i*k^2` from `(i-1)*k^2` and `k^2`.
    for (int i = 2; i <= A; ++i) {
        add_jump_edges(i * k2, n, (i - 1) * k2, k2);
    }

    std::cout << added_edges.size() << std::endl;
    for (const auto& t : added_edges) {
        std::cout << std::get<0>(t) << " " << std::get<1>(t) << " " << std::get<2>(t) << "\n";
    }

    return 0;
}