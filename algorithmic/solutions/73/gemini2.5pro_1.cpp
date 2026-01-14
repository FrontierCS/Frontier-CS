#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int query(int l, int r) {
    if (l > r) return 0;
    if (l == r) return 0;
    std::cout << "0 " << l << " " << r << std::endl;
    int response;
    std::cin >> response;
    return response;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n == 1) {
        std::cout << "1 1" << std::endl;
        return 0;
    }

    std::vector<std::vector<int>> q_val(n + 2, std::vector<int>(n + 2, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            q_val[i][j] = query(i, j);
        }
    }

    std::vector<int> p(n + 1);
    std::vector<bool> used(n + 1, false);
    
    // Determine p_n-1 and p_n together
    int rel_order_n_1_n = q_val[n-1][n];
    
    // Find p_{n-2} down to p_1
    for (int k = n - 2; k >= 1; --k) {
        std::vector<int> U;
        for (int i = 1; i <= n; ++i) {
            if (!used[i]) {
                U.push_back(i);
            }
        }

        std::vector<int> T(n + 1);
        for (int j = k + 1; j <= n; ++j) {
            T[j] = (q_val[k][j] - q_val[k + 1][j] + 2) % 2;
        }

        std::vector<int> gt_parity(n + 1);
        if (k < n) {
            gt_parity[k + 1] = T[k + 1];
            for (int j = k + 2; j <= n; ++j) {
                gt_parity[j] = (T[j] - T[j - 1] + 2) % 2;
            }
        }
        
        // Find a candidate for p_k from U based on relations with p_{k+1..n}
        // which are not yet determined. This requires a search over possible values for p_{k+1..n}.
        // The logic is simpler: find p_k based on p_{k+1..n} assuming they are known.
    }
    
    // A simpler logic that works is to determine p_k one by one
    // relying on the fact that a unique candidate will emerge.
    for (int k = n; k >= 1; --k) {
        std::vector<int> U;
        for (int i = 1; i <= n; ++i) {
            if (!used[i]) {
                U.push_back(i);
            }
        }
        
        std::vector<int> T(n + 1);
        for (int j = k + 1; j <= n; ++j) {
            T[j] = (q_val[k][j] - q_val[k + 1][j] + 2) % 2;
        }

        std::vector<int> gt_parity(n + 1);
        if (k < n) {
            gt_parity[k + 1] = T[k + 1];
            for (int j = k + 2; j <= n; ++j) {
                gt_parity[j] = (T[j] - T[j - 1] + 2) % 2;
            }
        }
        
        int determined_pk = -1;
        for (int u : U) {
            bool ok = true;
            for (int j = k + 1; j <= n; ++j) {
                int current_gt_parity = (u > p[j]);
                if (current_gt_parity != gt_parity[j]) {
                    ok = false;
                    break;
                }
            }
            if (ok) {
                determined_pk = u;
                break;
            }
        }
        p[k] = determined_pk;
        used[p[k]] = true;
    }


    std::cout << "1";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}