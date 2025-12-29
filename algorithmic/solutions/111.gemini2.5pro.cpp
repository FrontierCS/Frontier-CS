#include <iostream>
#include <vector>
#include <cmath>

// For n <= 10^7, the maximum possible XOR value between two elements a, b <= n
// is less than the smallest power of two that is greater than n.
// 2^23 < 10^7 < 2^24. So, any a,b <= n will have a,b < 2^24.
// Their XOR will also be less than 2^24.
const int MAX_XOR_VAL = 1 << 24;
std::vector<char> used_xors(MAX_XOR_VAL, 0);

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> s;

    for (int i = 1; i <= n; ++i) {
        bool is_valid = true;
        if (s.size() > 0) { // No checks needed for the first element
            for (int element : s) {
                if (used_xors[i ^ element]) {
                    is_valid = false;
                    break;
                }
            }
        }
        
        if (is_valid) {
            for (int element : s) {
                used_xors[i ^ element] = 1;
            }
            s.push_back(i);
        }
    }

    std::cout << s.size() << "\n";
    for (size_t i = 0; i < s.size(); ++i) {
        std::cout << s[i] << (i == s.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}