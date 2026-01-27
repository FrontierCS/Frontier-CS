#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <queue>

// Helper to map characters 'A'-'Z', '0'-'9' to 0-35
inline int char_to_int(char c) {
    if (c >= 'A' && c <= 'Z') {
        return c - 'A';
    }
    return c - '0' + 26;
}

// Helper to map 0-35 back to characters
inline char int_to_char(int i) {
    if (i < 26) {
        return 'A' + i;
    }
    return '0' + (i - 26);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::string s1, s2;
    std::cin >> s1 >> s2;

    const int n = s1.length();
    const int m = s2.length();
    
    const int ALPHABET_SIZE = 36;
    std::vector<int> pos1[ALPHABET_SIZE];
    std::vector<int> pos2[ALPHABET_SIZE];
    
    // Precompute positions of each character
    for (int i = 0; i < n; ++i) {
        pos1[char_to_int(s1[i])].push_back(i);
    }
    for (int i = 0; i < m; ++i) {
        pos2[char_to_int(s2[i])].push_back(i);
    }

    // Min-priority queue to find the best next character greedily.
    // Stores {metric, char_code}, where metric is max(index_in_s1, index_in_s2).
    using P = std::pair<int, int>;
    std::priority_queue<P, std::vector<P>, std::greater<P>> pq;

    // Pointers to the current search start in position lists for each character.
    std::vector<int> ptr1(ALPHABET_SIZE, 0);
    std::vector<int> ptr2(ALPHABET_SIZE, 0);

    // Initialize PQ with the first possible match for each character.
    for (int i = 0; i < ALPHABET_SIZE; ++i) {
        if (!pos1[i].empty() && !pos2[i].empty()) {
            pq.push({std::max(pos1[i][0], pos2[i][0]), i});
        }
    }
    
    int current_i = -1;
    int current_j = -1;
    std::string result;
    result.reserve((size_t(n) + m) / ALPHABET_SIZE + 1);

    while (!pq.empty()) {
        P top = pq.top();
        pq.pop();
        int val = top.first;
        int c_idx = top.second;
        
        // Find the actual next available positions for this character by advancing
        // pointers past the last matched positions.
        int i_idx = ptr1[c_idx];
        while (i_idx < pos1[c_idx].size() && pos1[c_idx][i_idx] <= current_i) {
            i_idx++;
        }
        
        int j_idx = ptr2[c_idx];
        while (j_idx < pos2[c_idx].size() && pos2[c_idx][j_idx] <= current_j) {
            j_idx++;
        }
        
        if (i_idx >= pos1[c_idx].size() || j_idx >= pos2[c_idx].size()) {
            continue; // This character is exhausted for future matches.
        }
        
        int next_i = pos1[c_idx][i_idx];
        int next_j = pos2[c_idx][j_idx];
        int new_val = std::max(next_i, next_j);
        
        if (new_val > val) {
            // The entry in PQ was stale (its metric was based on old positions).
            // Re-push with the current, valid value.
            pq.push({new_val, c_idx});
            // Update pointers to avoid re-scanning from the beginning next time.
            ptr1[c_idx] = i_idx;
            ptr2[c_idx] = j_idx;
            continue;
        }
        
        // This is the best available character. Greedily take it.
        result.push_back(int_to_char(c_idx));
        current_i = next_i;
        current_j = next_j;
        
        // Advance pointers for the matched character to its next position.
        ptr1[c_idx] = i_idx + 1;
        ptr2[c_idx] = j_idx + 1;
        
        // Push the next candidate for this character into the PQ.
        if (ptr1[c_idx] < pos1[c_idx].size() && ptr2[c_idx] < pos2[c_idx].size()) {
            pq.push({std::max(pos1[c_idx][ptr1[c_idx]], pos2[c_idx][ptr2[c_idx]]), c_idx});
        }
    }
    
    std::cout << result << "\n";
    
    return 0;
}