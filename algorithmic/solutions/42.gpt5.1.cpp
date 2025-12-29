#include <iostream>
#include <iomanip>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);

    long long n;
    if (!(std::cin >> n)) return 0;

    long long L = 0;
    while (L * L < n) ++L;

    std::cout << std::fixed << std::setprecision(6);
    std::cout << static_cast<double>(L) << "\n";

    for (long long i = 0; i < n; ++i) {
        long long row = i / L;
        long long col = i % L;
        double x = 0.5 + static_cast<double>(col);
        double y = 0.5 + static_cast<double>(row);
        double a = 0.0;
        std::cout << x << " " << y << " " << a << "\n";
    }

    return 0;
}