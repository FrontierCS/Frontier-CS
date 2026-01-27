#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

// Maps a character from the set {'A'-'Z', '0'-'9'} to an integer index [0, 35].
inline int char_to_int(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }
    return c - '0' + 26;
}

// Finds a common subsequence by greedily matching characters from string 'a' in string 'b'.
// This function has a time complexity of O(|a| + |b|).
std::string solve_greedy(const std::string& a, const std::string& b) {
    // Precompute positions of each character in string 'b' for fast lookups.
    // pos[i] stores a sorted list of indices where the i-th character of the alphabet appears in 'b'.
    std::vector<std::vector<int>> pos(36);
    for (int i = 0; i < b.length(); ++i) {
        pos[char_to_int(b[i])].push_back(i);
    }

    std::string res;
    // Reserve memory to avoid reallocations. A safe upper bound for LCS length is min(|a|, |b|).
    res.reserve(std::min(a.length(), b.length()));
    
    int last_pos_b = -1;
    // 'p' stores pointers for each character's position vector to avoid re-scanning from the beginning.
    std::vector<int> p(36, 0);

    for (char c : a) {
        int char_idx = char_to_int(c);
        
        // Find the next occurrence of 'c' in 'b' after 'last_pos_b' by advancing the pointer p[char_idx].
        while (p[char_idx] < pos[char_idx].size() && pos[char_idx][p[char_idx]] <= last_pos_b) {
            p[char_idx]++;
        }
        
        // If a valid position is found, append the character to the result and update the last position.
        if (p[char_idx] < pos[char_idx].size()) {
            res.push_back(c);
            last_pos_b = pos[char_idx][p[char_idx]];
            p[char_idx]++; // Move pointer for the next search of this character.
        }
    }
    return res;
}

int main() {
    // Fast I/O for large inputs.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string s1, s2;
    std::cin >> s1 >> s2;

    // Run the greedy algorithm in both directions to get two candidate subsequences.
    std::string res1 = solve_greedy(s1, s2);
    std::string res2 = solve_greedy(s2, s1);

    // Output the longer of the two results.
    if (res1.length() >= res2.length()) {
        std::cout << res1 << std::endl;
    } else {
        std::cout << res2 << std::endl;
    }

    return 0;
}