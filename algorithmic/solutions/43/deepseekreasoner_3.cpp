#include <iostream>
#include <string>

int main() {
    int N = 2, M = 98;
    std::cout << N << " " << M << std::endl;
    std::string row1 = "PBB" + std::string(93, '.') + "SS";
    std::string row2 = ".BB" + std::string(93, '.') + "SS";
    std::cout << row1 << std::endl;
    std::cout << row2 << std::endl;
    return 0;
}