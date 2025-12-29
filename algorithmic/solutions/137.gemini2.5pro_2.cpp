#include <iostream>
#include <vector>
#include <string>

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Define grid dimensions. 19x19 is used for a clear center point.
    // 20x20 would also be a valid choice.
    int n = 19;
    int m = 19;

    // Print grid dimensions as per the output format.
    std::cout << n << " " << m << std::endl;

    // Create the map as a vector of strings, initialized with walls ('0').
    std::vector<std::string> map(n, std::string(m, '0'));

    // Determine the center row and column. For a 19x19 grid, this is index 9.
    int center_r = n / 2;
    int center_c = m / 2;

    // Create the vertical arm of the cross.
    for (int i = 0; i < n; ++i) {
        map[i][center_c] = '1';
    }

    // Create the horizontal arm of the cross.
    // The center cell (map[center_r][center_c]) is set to '1' twice, which is fine.
    for (int j = 0; j < m; ++j) {
        map[center_r][j] = '1';
    }

    // Print the generated map row by row.
    for (int i = 0; i < n; ++i) {
        std::cout << map[i] << std::endl;
    }

    return 0;
}