#include <iostream>

int main() {
    int n = 20, m = 20;
    std::cout << n << " " << m << "\n";
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= m; ++j) {
            if (i == 10) {
                std::cout << '1';
            } else if (j % 2 == 0) {
                std::cout << (i <= 9 ? '1' : '0');
            } else {
                std::cout << (i >= 11 ? '1' : '0');
            }
        }
        std::cout << "\n";
    }
    return 0;
}