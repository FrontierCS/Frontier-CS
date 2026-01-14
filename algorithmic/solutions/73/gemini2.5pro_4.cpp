#include <iostream>
#include <vector>
#include <numeric>

int query(int l, int r) {
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

    std::vector<std::vector<int>> inv_parity(n + 1, std::vector<int>(n + 1, 0));

    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            inv_parity[i][j] = query(i, j);
        }
    }

    std::vector<std::vector<int>> is_greater(n + 1, std::vector<int>(n + 1, 0));

    for (int i = 2; i <= n; ++i) {
        std::vector<int> C(i);
        for (int j = 1; j < i; ++j) {
            C[j] = (inv_parity[j][i] - inv_parity[j][i - 1] + 2) % 2;
        }

        is_greater[i - 1][i] = C[i - 1];
        for (int j = i - 2; j >= 1; --j) {
            is_greater[j][i] = (C[j] - C[j + 1] + 2) % 2;
        }
    }
    
    std::vector<int> p(n + 1);
    for (int i = 1; i <= n; ++i) {
        int smaller_count = 0;
        for (int j = 1; j < i; ++j) {
            if (!is_greater[j][i]) {
                smaller_count++;
            }
        }
        for (int j = i + 1; j <= n; ++j) {
            if (is_greater[i][j]) {
                smaller_count++;
            }
        }
        p[i] = smaller_count + 1;
    }

    std::cout << "1";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << p[i];
    }
    std::cout << std::endl;

    return 0;
}