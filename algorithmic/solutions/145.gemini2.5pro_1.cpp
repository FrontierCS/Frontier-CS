#include <iostream>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int task_type;
    std::cin >> task_type;
    
    // The following grid is a valid Number Loop puzzle with a unique solution.
    // It only uses digits from 1 to 3, so it's a valid solution for both
    // the small task (digits 0-3) and the large task (digits 1-3).
    // The input 'task_type' is read but not used, as the output is the same for both cases.
    std::cout << "1   3   212 \n";
    std::cout << "21 21  3   1\n";
    std::cout << "2 1 3  2   1\n";
    std::cout << "2 3 2  3222 \n";
    std::cout << "1 1 1  1    \n";
    std::cout << "2   2  2    \n";
    std::cout << "            \n";
    std::cout << "1  3   22122\n";
    std::cout << "2 2      1  \n";
    std::cout << "22   1 2 2  \n";
    std::cout << "1 2  2 1 3  \n";
    std::cout << "2  2 121 1  \n";
    
    return 0;
}