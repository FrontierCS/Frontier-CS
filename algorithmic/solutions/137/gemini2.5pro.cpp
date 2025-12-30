#include <iostream>
#include <vector>
#include <string>

int main() {
    // Use fast I/O in competitive programming.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Define the maximum grid dimensions as per the problem statement.
    const int n = 20;
    const int m = 20;

    // Print the grid dimensions.
    std::cout << n << " " << m << '\n';

    // Create a grid initialized with walls ('0').
    std::vector<std::string> grid(n, std::string(m, '0'));

    // Define the center for the cross. A non-perfect center is fine.
    const int center_r = 10;
    const int center_c = 10;

    // Create the vertical bar of the cross by setting cells to empty ('1').
    for (int i = 0; i < n; ++i) {
        grid[i][center_c] = '1';
    }
    
    // Create the horizontal bar of the cross.
    for (int j = 0; j < m; ++j) {
        grid[center_r][j] = '1';
    }

    // Print the final map.
    for (int i = 0; i < n; ++i) {
        std::cout << grid[i] << '\n';
    }

    return 0;
}