#include <iostream>
#include <vector>
#include <numeric>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long x;
    std::cin >> x;

    // The grid size n is determined by the number of bits in x.
    // 61 bits are enough for x up to 10^18. Each bit needs a new "layer" (row).
    // The number of columns will be similar. A size of 100 is safe.
    int n = 100;
    std::vector<std::vector<int>> grid(n + 1, std::vector<int>(n + 1, 0));
    
    // current_row tracks the main "lane" for path construction.
    int current_row = 1;
    
    // We process bits from MSB side for construction, but the value x is built up LSB-first.
    // So we iterate through bits of x from 0 to 60.
    for (int k = 0; k < 61; ++k) {
        // Move to the next layer.
        // This is the default connection, representing S_new = S_old + f_old.
        grid[current_row][current_row + 1] = 1;
        
        // If the k-th bit of x is set, we want to double the total paths.
        // This is done by adding a path from every previous layer's start.
        if ((x >> k) & 1) {
            for (int i = 1; i < current_row; ++i) {
                grid[i][current_row + 1] = 1;
            }
        }
        current_row++;
    }

    // Finally, connect all active rows to the destination column to sum up all paths.
    for (int i = 1; i <= current_row; ++i) {
        grid[i][current_row] = 1;
    }

    // Output the grid.
    std::cout << current_row << std::endl;
    for (int i = 1; i <= current_row; ++i) {
        for (int j = 1; j <= current_row; ++j) {
            std::cout << grid[i][j] << (j == current_row ? "" : " ");
        }
        std::cout << std::endl;
    }

    return 0;
}