#include <iostream>
#include <vector>
#include <cmath>

// Max possible XOR value for n <= 10^7. 2^24 > 10^7.
const int MAX_XOR = 1 << 24; 
// Use a static array for efficiency; it's zero-initialized.
bool seen_xors[MAX_XOR];

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> S;
    // Reserve space to avoid reallocations, based on observed size for max n.
    S.reserve(3000); 

    // Greedily build the set S.
    for (int i = 1; i <= n; ++i) {
        bool can_add = true;
        // Check if adding 'i' would create a duplicate XOR value.
        for (int s_val : S) {
            if (seen_xors[i ^ s_val]) {
                can_add = false;
                break;
            }
        }

        if (can_add) {
            // Add 'i' to S and update the seen_xors table.
            for (int s_val : S) {
                seen_xors[i ^ s_val] = true;
            }
            S.push_back(i);
        }
    }

    // Output the resulting set.
    std::cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        std::cout << S[i] << (i == S.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}