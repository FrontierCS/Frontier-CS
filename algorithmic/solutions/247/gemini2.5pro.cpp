#include <iostream>
#include <vector>
#include <numeric>
#include <cmath>

void apply_op(int i, int j, std::vector<int>& a) {
    int tmp_i = a[i-1];
    int tmp_j = a[j-1];
    a[i-1] = tmp_j - 1;
    a[j-1] = tmp_i + 1;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;
    std::vector<int> a(n), b(n);
    long long sum_a = 0, sum_b = 0;
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
        sum_a += a[i];
    }
    for (int i = 0; i < n; ++i) {
        std::cin >> b[i];
        sum_b += b[i];
    }

    if (sum_a != sum_b) {
        std::cout << "No\n";
        return 0;
    }

    std::vector<std::pair<int, int>> ops;

    for (int k = 0; k < 40000; ++k) {
        if (a == b) {
            break;
        }

        bool found_op = false;
        
        // Strategy: prioritize direct moves that move values from a "source" (A_i > B_i)
        // to a "sink" (A_j < B_j), as this makes clear progress towards the goal.
        int best_i = -1, best_j = -1;
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                // Case 1: i is a source, j is a sink.
                // Operation (i,j) decreases A_i and increases A_j if A_i >= A_j.
                if (a[i-1] > b[i-1] && a[j-1] < b[j-1]) {
                    if (a[i-1] >= a[j-1]) {
                        best_i = i; best_j = j;
                        goto found_direct_move;
                    }
                }
                // Case 2: i is a sink, j is a source.
                // Operation (i,j) increases A_i and decreases A_j if A_j > A_i + 1.
                if (a[i-1] < b[i-1] && a[j-1] > b[j-1]) {
                    if (a[j-1] > a[i-1] + 1) {
                       best_i = i; best_j = j;
                       goto found_direct_move;
                    }
                }
            }
        }
        
    found_direct_move:
        if (best_i != -1) {
            apply_op(best_i, best_j, a);
            ops.push_back({best_i, best_j});
            found_op = true;
        }

        if (found_op) {
            continue;
        }

        // If no direct source-sink move is possible, we might be in a state
        // that requires an intermediate "stirring" move.
        // We apply any operation that is not an identity transformation to change the state.
        for (int i = 1; i <= n; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                // Operation (i,j) is an identity if A_j = A_i + 1.
                // So we apply it if A_j != A_i + 1.
                if (a[j-1] != a[i-1] + 1) {
                    apply_op(i, j, a);
                    ops.push_back({i, j});
                    found_op = true;
                    break;
                }
            }
            if (found_op) break;
        }
    }

    if (a == b) {
        std::cout << "Yes\n";
        std::cout << ops.size() << "\n";
        for (const auto& p : ops) {
            std::cout << p.first << " " << p.second << "\n";
        }
    } else {
        // This case should not be reached if the problem is always solvable
        // when sum(A) == sum(B).
        std::cout << "No\n";
    }

    return 0;
}