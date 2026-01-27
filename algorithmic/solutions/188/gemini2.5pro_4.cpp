#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

// Maps 'A'-'Z' to 0-25 and '0'-'9' to 26-35.
// The problem statement guarantees characters are in this set.
inline int char_to_int(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }
    return 26 + (c - '0');
}

// Precomputes the positions of each character in a string.
void precompute_positions(const std::string& s, std::vector<std::vector<int>>& pos) {
    pos.assign(36, std::vector<int>());
    for (size_t i = 0; i < s.length(); ++i) {
        pos[char_to_int(s[i])].push_back(i);
    }
}

// Finds a common subsequence using a greedy forward scan.
// It iterates through string 'a' and for each character, finds its earliest possible match in 'b'.
std::string run_greedy_forward(const std::string& a, const std::string& b, const std::vector<std::vector<int>>& pos_b) {
    std::string res;
    if (a.empty() || b.empty()) return res;
    res.reserve(std::min(a.length(), b.length()));
    int current_pos_b = -1;
    std::vector<int> ptrs(36, 0);

    for (char c_a : a) {
        int char_idx = char_to_int(c_a);
        const auto& p = pos_b[char_idx];
        
        while (ptrs[char_idx] < p.size() && p[ptrs[char_idx]] <= current_pos_b) {
            ptrs[char_idx]++;
        }

        if (ptrs[char_idx] < p.size()) {
            res += c_a;
            current_pos_b = p[ptrs[char_idx]];
            ptrs[char_idx]++;
        }
    }
    return res;
}

// Finds a common subsequence using a greedy backward scan.
// This is equivalent to running the forward greedy on reversed strings.
std::string run_greedy_backwards(const std::string& a, const std::string& b, const std::vector<std::vector<int>>& pos_b) {
    std::string res;
    if (a.empty() || b.empty()) return res;
    res.reserve(std::min(a.length(), b.length()));
    int current_pos_b = b.length();
    
    std::vector<int> ptrs(36);
    for(int i = 0; i < 36; ++i) {
        if (!pos_b[i].empty()) {
            ptrs[i] = pos_b[i].size() - 1;
        }
    }

    for (int i = a.length() - 1; i >= 0; --i) {
        int char_idx = char_to_int(a[i]);
        const auto& p = pos_b[char_idx];
        if (p.empty()) continue;
        
        while (ptrs[char_idx] >= 0 && p[ptrs[char_idx]] >= current_pos_b) {
            ptrs[char_idx]--;
        }

        if (ptrs[char_idx] >= 0) {
            res += a[i];
            current_pos_b = p[ptrs[char_idx]];
            ptrs[char_idx]--;
        }
    }
    std::reverse(res.begin(), res.end());
    return res;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string s1, s2;
    std::cin >> s1 >> s2;

    std::vector<std::vector<int>> pos1, pos2;
    precompute_positions(s1, pos1);
    precompute_positions(s2, pos2);

    std::string best_res = "";

    // Strategy 1: Greedy forward on (S1, S2)
    std::string res1 = run_greedy_forward(s1, s2, pos2);
    if (res1.length() > best_res.length()) {
        best_res = res1;
    }

    // Strategy 2: Greedy forward on (S2, S1)
    std::string res2 = run_greedy_forward(s2, s1, pos1);
    if (res2.length() > best_res.length()) {
        best_res = res2;
    }
    
    // Strategy 3: Greedy backward on (S1, S2)
    // This is equivalent to greedy forward on (reverse(S1), reverse(S2))
    std::string res3 = run_greedy_backwards(s1, s2, pos2);
    if (res3.length() > best_res.length()) {
        best_res = res3;
    }

    // Strategy 4: Greedy backward on (S2, S1)
    // This is equivalent to greedy forward on (reverse(S2), reverse(S1))
    std::string res4 = run_greedy_backwards(s2, s1, pos1);
    if (res4.length() > best_res.length()) {
        best_res = res4;
    }

    std::cout << best_res << std::endl;

    return 0;
}