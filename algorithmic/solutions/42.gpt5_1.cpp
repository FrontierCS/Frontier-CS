#include <iostream>
#include <iomanip>
#include <cmath>

int main() {
    std::ios::sync_with_stdio(false);
    std::cin.tie(nullptr);
    
    long long n;
    if (!(std::cin >> n)) return 0;
    
    long long k = (long long)std::ceil(std::sqrt((long double)n));
    double L = static_cast<double>(k);
    
    std::cout.setf(std::ios::fixed);
    std::cout << std::setprecision(6) << L << "\n";
    
    long long cnt = 0;
    for (long long y = 0; y < k && cnt < n; ++y) {
        for (long long x = 0; x < k && cnt < n; ++x) {
            double xi = x + 0.5;
            double yi = y + 0.5;
            double ai = 0.0;
            std::cout << xi << " " << yi << " " << ai << "\n";
            ++cnt;
        }
    }
    return 0;
}