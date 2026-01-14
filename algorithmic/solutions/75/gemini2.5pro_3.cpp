#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

void solve() {
    int b, w, x, y;
    std::cin >> b >> w >> x >> y;

    if (w >= b) {
        int M = w;
        int r = 2;
        int c = 2 * M;
        std::cout << r << " " << c << std::endl;
        std::vector<std::string> grid(r, std::string(c, ' '));

        // Create base grid with M black and M white components
        for (int j = 0; j < M; ++j) {
            grid[0][2 * j] = '@';
            grid[0][2 * j + 1] = '.';
            grid[1][2 * j] = '@';
            grid[1][2 * j + 1] = '.';
        }

        // We have w black components, need b. Merge w-b of them.
        for (int k = 0; k < w - b; ++k) {
            // Change a '.' to '@' to bridge two black components
            grid[0][2 * k + 1] = '@';
        }
        
        for (int i = 0; i < r; ++i) {
            std::cout << grid[i] << std::endl;
        }

    } else { // b > w
        int M = b;
        int r = 2;
        int c = 2 * M;
        std::cout << r << " " << c << std::endl;
        std::vector<std::string> grid(r, std::string(c, ' '));

        // Create base grid with M black and M white components
        for (int j = 0; j < M; ++j) {
            grid[0][2 * j] = '@';
            grid[0][2 * j + 1] = '.';
            grid[1][2 * j] = '@';
            grid[1][2 * j + 1] = '.';
        }

        // We have b white components, need w. Merge b-w of them.
        for (int k = 0; k < b - w; ++k) {
            // Change an '@' to '.' to bridge two white components
            grid[0][2 * k + 2] = '.';
        }

        for (int i = 0; i < r; ++i) {
            std::cout << grid[i] << std::endl;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    solve();
    return 0;
}