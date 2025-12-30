#include <iostream>

void solve_small_task() {
    std::cout << "2   1   111 " << std::endl;
    std::cout << "10 00  0   1" << std::endl;
    std::cout << "1 0 0  0   1" << std::endl;
    std::cout << "1 0 0  0000 " << std::endl;
    std::cout << "1 0 0  0    " << std::endl;
    std::cout << "1   0  0    " << std::endl;
    std::cout << "            " << std::endl;
    std::cout << "1  0   00001" << std::endl;
    std::cout << "1 0      0  " << std::endl;
    std::cout << "10   0 0 0  " << std::endl;
    std::cout << "1 0  0 0 0  " << std::endl;
    std::cout << "1  1   111 1 " << std::endl;
}

void solve_large_task() {
    std::cout << "3   2   111 " << std::endl;
    std::cout << "12 12  3   1" << std::endl;
    std::cout << "2 3 2  2   1" << std::endl;
    std::cout << "1 2 2  1111 " << std::endl;
    std::cout << "2 2 1  1    " << std::endl;
    std::cout << "1   1  3    " << std::endl;
    std::cout << "            " << std::endl;
    std::cout << "2  1   11111" << std::endl;
    std::cout << "1 1      1  " << std::endl;
    std::cout << "11   1 2 1  " << std::endl;
    std::cout << "1 2  1 1 2  " << std::endl;
    std::cout << "1  2   222 2 " << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int task_type;
    std::cin >> task_type;

    if (task_type == 0) {
        solve_small_task();
    } else {
        solve_large_task();
    }

    return 0;
}