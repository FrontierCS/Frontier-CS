#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    const int n = 20;
    const int m = 20;

    std::cout << n << " " << m << std::endl;

    std::vector<std::string> grid(n, std::string(m, '0'));

    for (int i = 0; i < n; i += 2) {
        for (int j = 0; j < m; ++j) {
            grid[i][j] = '1';
        }
    }

    for (int k = 0; k < 9; ++k) {
        if (k % 2 == 0) {
            grid[2 * k + 1][m - 1] = '1';
        } else {
            grid[2 * k + 1][0] = '1';
        }
    }

    for (int i = 0; i < n; ++i) {
        std::cout << grid[i] << std::endl;
    }

    return 0;
}