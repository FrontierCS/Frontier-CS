#include <iostream>
#include <string>

int main() {
    std::cout << "2 98" << std::endl;
    std::string row0 = "SS" + std::string(93, '.') + "BBP";
    std::string row1 = "SS" + std::string(93, '.') + "BB.";
    std::cout << row0 << std::endl;
    std::cout << row1 << std::endl;
    return 0;
}