#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

// The maximum value of i we might test is estimated to be around 12000 for m=2500.
// The maximum XOR value would then be less than 16384. 1<<16 is a safe size.
const int MAX_XOR_VAL = 1 << 16;
bool used_xors[MAX_XOR_VAL];

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    int m_req = static_cast<int>(floor(sqrt(n / 2.0)));
    
    // A non-empty subset of {1...n} is required.
    // If n=1, m_req=0. We should still output a valid set, e.g., {1}.
    if (m_req == 0) {
        m_req = 1;
    }
    
    std::vector<int> S;
    S.reserve(m_req);

    for (int i = 1; S.size() < m_req; ++i) {
        if (i > n) {
            // This safeguard ensures all elements are within the [1, n] range.
            // Based on analysis, this condition is unlikely to be met for the given constraints of n.
            break;
        }
        
        bool possible = true;
        for (int s_val : S) {
            if (used_xors[i ^ s_val]) {
                possible = false;
                break;
            }
        }
        
        if (possible) {
            for (int s_val : S) {
                used_xors[i ^ s_val] = true;
            }
            S.push_back(i);
        }
    }

    std::cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        std::cout << S[i] << (i == S.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}