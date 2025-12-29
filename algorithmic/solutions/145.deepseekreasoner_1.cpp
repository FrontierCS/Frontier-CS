#include <iostream>
#include <string>

int main() {
    int task;
    std::cin >> task;
    
    if (task == 0) {
        // Small Task: digits 0-3, using mainly 2
        std::cout << "2   2   222 \n";
        std::cout << "22 22  2   2\n";
        std::cout << "2 2 2  2   2\n";
        std::cout << "2 2 2  2222 \n";
        std::cout << "2 2 2  2    \n";
        std::cout << "2   2  2    \n";
        std::cout << "            \n";
        std::cout << "2  2   22222\n";
        std::cout << "2 2      2  \n";
        std::cout << "22   2 2 2  \n";
        std::cout << "2 2  2 2 2  \n";
        std::cout << "2  2 222 2  \n";
    } else {
        // Large Task: digits 1-3, using mainly 3
        std::cout << "3   3   333 \n";
        std::cout << "33 33  3   3\n";
        std::cout << "3 3 3  3   3\n";
        std::cout << "3 3 3  3333 \n";
        std::cout << "3 3 3  3    \n";
        std::cout << "3   3  3    \n";
        std::cout << "            \n";
        std::cout << "3  3   33333\n";
        std::cout << "3 3      3  \n";
        std::cout << "33   3 3 3  \n";
        std::cout << "3 3  3 3 3  \n";
        std::cout << "3  3 333 3  \n";
    }
    
    return 0;
}