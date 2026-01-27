#include <iostream>

int main() {
    int n;
    std::cin >> n;
    if (n <= 3) {
        std::cout << 0 << std::endl;
        return 0;
    }
    int L = (n + 2) / 3; // ceil(n/3)
    long long m = 0;
    for (int s = 2; s <= L; ++s) {
        m += n - s + 1;
    }
    std::cout << m << '\n';
    for (int s = 2; s <= L; ++s) {
        for (int i = 0; i <= n - s; ++i) {
            int w = i + s / 2; // for even s this is exact, for odd it floors
            if (s % 2 == 1) {
                w = i + (s - 1) / 2;
            }
            std::cout << i << ' ' << w << ' ' << i + s << '\n';
        }
    }
    return 0;
}