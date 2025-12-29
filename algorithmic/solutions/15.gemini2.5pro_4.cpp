#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Global buffers to avoid repeated allocations
std::vector<int> p_copy;

// Applies operation (x, y) to permutation p and updates pos array
void apply_op_internal(std::vector<int>& p, int x, int y, std::vector<int>& pos) {
    int n = p.size();
    
    // Suffix -> new Prefix
    for (int i = 0; i < y; ++i) {
        p_copy[i] = p[n - y + i];
    }
    // Middle -> new Middle
    for (int i = 0; i < n - x - y; ++i) {
        p_copy[y + i] = p[x + i];
    }
    // Prefix -> new Suffix
    for (int i = 0; i < x; ++i) {
        p_copy[n - x + i] = p[i];
    }

    p = p_copy;

    // Update positions of all elements
    for (int i = 0; i < n; ++i) {
        pos[p[i]] = i;
    }
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> p(n);
    std::vector<int> pos(n + 1);
    for (int i = 0; i < n; ++i) {
        std::cin >> p[i];
        pos[p[i]] = i;
    }

    p_copy.resize(n);

    std::vector<std::pair<int, int>> ops;

    // Helper lambda to apply and record an operation
    auto apply_op = [&](int x, int y) {
        ops.push_back({x, y});
        apply_op_internal(p, x, y, pos);
    };

    for (int i = 1; i <= n; ++i) {
        int k = pos[i]; // current position of value i
        int j = i - 1;   // target position for value i

        if (k == j) {
            continue;
        }

        if (k > j + 1) {
            // Case 1: k is far to the right of j.
            // Move p[k] to p[j] in one op.
            apply_op(1, n - k + j);
        } else if (k < j) {
            // Case 2: k is to the left of j.
            // First, move p[k] to the end.
            if (k < n - 1) {
                apply_op(k + 1, 1);
            } else { // k is already at the end, move it slightly to apply next op
                apply_op(n - 1, 1);
            }
            
            k = pos[i]; // update k's position

            // Now k is at or near the end, so k > j.
            if (k > j + 1) {
                apply_op(1, n - k + j);
            } else { // k is now j+1, swap needed.
                // Move p[j] out of the way to position 0 (if not already there)
                if (j > 0) {
                    apply_op(1, n - j);
                    k = pos[i]; // update k
                    apply_op(1, n - k + j);
                } else { // j=0
                    apply_op(2, 1);
                    k = pos[i];
                    apply_op(1, n - k);
                }
            }
        } else { // k == j + 1, adjacent swap needed.
            // A 3-op sequence for adjacent swap p[j] and p[j+1]
            if (j + 1 < n - 1) { // generic case
                apply_op(j + 2, 1);
                apply_op(n - 2, 1);
                apply_op(2, n - (j + 2));
            } else { // swapping last two elements
                apply_op(n - 1, 1);
                apply_op(1, n - 2);
                apply_op(2, 1);
            }
        }
    }

    std::cout << ops.size() << "\n";
    for (const auto& op : ops) {
        std::cout << op.first << " " << op.second << "\n";
    }

    return 0;
}