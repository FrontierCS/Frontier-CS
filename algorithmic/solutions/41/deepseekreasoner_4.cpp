#include <iostream>

int main() {
    long long n;
    std::cin >> n;

    int k = 0;
    long long val = 1;
    while (val <= n) {
        ++k;
        val <<= 1;
    }

    std::cout << k << "\n";
    val = 1;
    for (int i = 0; i < k; ++i) {
        if (i) std::cout << " ";
        std::cout << val;
        val <<= 1;
    }
    std::cout << "\n";

    return 0;
}