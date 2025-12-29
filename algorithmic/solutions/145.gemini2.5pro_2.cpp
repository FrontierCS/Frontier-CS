#include <iostream>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    int task_type;
    std::cin >> task_type;

    if (task_type == 0) {
        // Solution for Small Task (digits 0-3)
        std::cout << "2   1   111 \n";
        std::cout << "31 11  1   1\n";
        std::cout << "3 1 2  3   1\n";
        std::cout << "1 1 1  1111 \n";
        std::cout << "3 1 1  1    \n";
        std::cout << "1   3  2    \n";
        std::cout << "            \n";
        std::cout << "1  3   11111\n";
        std::cout << "1 1      1  \n";
        std::cout << "11   1 1 1  \n";
        std::cout << "1 1  1 1 1  \n";
        std::cout << "1  1 111 1  \n";
    } else {
        // Solution for Large Task (digits 1-3)
        std::cout << "3   1   111 \n";
        std::cout << "31 11  1   1\n";
        std::cout << "3 1 3  3   1\n";
        std::cout << "1 1 1  1111 \n";
        std::cout << "3 1 1  1    \n";
        std::cout << "1   3  3    \n";
        std::cout << "            \n";
        std::cout << "1  3   11111\n";
        std::cout << "1 1      1  \n";
        std::cout << "11   1 1 1  \n";
        std::cout << "1 1  1 1 1  \n";
        std::cout << "1  1 111 1  \n";
    }

    return 0;
}