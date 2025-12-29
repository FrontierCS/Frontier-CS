#include <iostream>
#include <vector>
#include <string>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int task_type;
    std::cin >> task_type;

    if (task_type == 0) {
        // Solution for the Small Task (digits 0-3)
        std::vector<std::string> grid = {
            "3   1   202 ",
            "33 13  3   0",
            "3 2 1  1   3",
            "1 2 2  3222 ",
            "2 1 2  3    ",
            "1   3  2    ",
            "            ",
            "   1 2 2    ",
            "2        2  ",
            "33   0 1 2  ",
            "2 2  1 1 2  ",
            "1  2 212 1  "
        };
        for (const auto& row : grid) {
            std::cout << row << '\n';
        }
    } else {
        // Solution for the Large Task (digits 1-3)
        std::vector<std::string> grid = {
            "1   2   312 ",
            "33 13  3   1",
            "3 2 1  1   3",
            "1 2 2  3222 ",
            "2 1 2  3    ",
            "1   3  2    ",
            "            ",
            "   1 2 2    ",
            "2        2  ",
            "33   1 1 2  ",
            "2 2  1 1 2  ",
            "1  2 212 1  "
        };
        for (const auto& row : grid) {
            std::cout << row << '\n';
        }
    }

    return 0;
}