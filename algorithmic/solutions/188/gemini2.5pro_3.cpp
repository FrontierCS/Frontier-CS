#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

// Function to map characters 'A'-'Z', '0'-'9' to an integer index [0, 35]
inline int char_to_int(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }
    // Assumes c is a digit '0'-'9' based on problem constraints
    return c - '0' + 26;
}

// The core greedy algorithm
// Iterates through s_iterate and finds the earliest possible match for each character
// based on precomputed character positions `pos_search`.
// This is an O(|s_iterate| + |s_search|) implementation where |s_search| is the
// length of the string from which pos_search was built.
std::string solve_greedy(const std::string& s_iterate, const std::vector<std::vector<int>>& pos_search) {
    std::string res;
    if (s_iterate.empty()) {
        return res;
    }
    res.reserve(s_iterate.length());
    
    int last_search_idx = -1;
    std::vector<int> ptrs(36, 0);

    for (char c_iterate : s_iterate) {
        int char_idx = char_to_int(c_iterate);
        
        const std::vector<int>& positions = pos_search[char_idx];
        int& p = ptrs[char_idx];
        
        // Advance pointer to the first available position
        while (static_cast<size_t>(p) < positions.size() && positions[p] <= last_search_idx) {
            p++;
        }
        
        if (static_cast<size_t>(p) < positions.size()) {
            res.push_back(c_iterate);
            last_search_idx = positions[p];
            p++;
        }
    }
    return res;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string s1, s2;
    std::cin >> s1 >> s2;

    // Precompute character positions for both strings
    std::vector<std::vector<int>> pos1(36);
    std::vector<std::vector<int>> pos2(36);

    for (size_t i = 0; i < s1.length(); ++i) {
        pos1[char_to_int(s1[i])].push_back(i);
    }
    for (size_t i = 0; i < s2.length(); ++i) {
        pos2[char_to_int(s2[i])].push_back(i);
    }

    // Run greedy algorithm in both directions:
    // 1. Iterate through s1, search in s2
    // 2. Iterate through s2, search in s1
    std::string res1 = solve_greedy(s1, pos2);
    std::string res2 = solve_greedy(s2, pos1);

    // Output the longer result
    if (res1.length() >= res2.length()) {
        std::cout << res1 << '\n';
    } else {
        std::cout << res2 << '\n';
    }

    return 0;
}