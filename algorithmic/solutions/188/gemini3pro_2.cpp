#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Character mapping: A-Z -> 0-25, 0-9 -> 26-35
inline int get_id(char c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= '0' && c <= '9') return c - '0' + 26;
    return -1;
}

inline char get_char(int id) {
    if (id < 26) return 'A' + id;
    return '0' + (id - 26);
}

const int ALPHABET = 36;
const int INF = 1e9;

int main() {
    fast_io();

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = s1.length();
    int m = s2.length();

    // Frequency counts for exact memory reservation
    vector<int> cnt1(ALPHABET, 0);
    vector<int> cnt2(ALPHABET, 0);
    
    for (char c : s1) cnt1[get_id(c)]++;
    for (char c : s2) cnt2[get_id(c)]++;

    // Store positions of each character
    static vector<int> pos1[ALPHABET];
    static vector<int> pos2[ALPHABET];

    for (int i = 0; i < ALPHABET; i++) {
        pos1[i].reserve(cnt1[i]);
        pos2[i].reserve(cnt2[i]);
    }

    for (int i = 0; i < n; i++) {
        pos1[get_id(s1[i])].push_back(i);
    }
    for (int i = 0; i < m; i++) {
        pos2[get_id(s2[i])].push_back(i);
    }

    // Pointers to the current valid position in the pos lists
    vector<int> ptr1(ALPHABET, 0);
    vector<int> ptr2(ALPHABET, 0);

    int curr1 = -1; // Current index in s1
    int curr2 = -1; // Current index in s2

    string z;
    z.reserve(min(n, m));

    while (true) {
        int best_c = -1;
        long long min_score = -1;
        int best_p1 = -1;
        int best_p2 = -1;
        int best_diff = INF;

        // Iterate over all possible characters for the next match
        for (int c = 0; c < ALPHABET; c++) {
            // Lazily advance pointers to find the first occurrence after curr1/curr2
            while (ptr1[c] < pos1[c].size() && pos1[c][ptr1[c]] <= curr1) {
                ptr1[c]++;
            }
            while (ptr2[c] < pos2[c].size() && pos2[c][ptr2[c]] <= curr2) {
                ptr2[c]++;
            }

            // If character exists in both remaining substrings
            if (ptr1[c] < pos1[c].size() && ptr2[c] < pos2[c].size()) {
                int p1 = pos1[c][ptr1[c]];
                int p2 = pos2[c][ptr2[c]];

                int d1 = p1 - curr1;
                int d2 = p2 - curr2;

                // Heuristic: Minimize sum of jumps (d1 + d2)
                // This balances preserving length in both strings.
                long long score = (long long)d1 + d2;
                
                // Secondary metric: Minimize max(d1, d2) to stay close to the diagonal
                int max_d = std::max(d1, d2);

                if (best_c == -1 || score < min_score) {
                    min_score = score;
                    best_c = c;
                    best_p1 = p1;
                    best_p2 = p2;
                    best_diff = max_d;
                } else if (score == min_score) {
                    if (max_d < best_diff) {
                        best_c = c;
                        best_p1 = p1;
                        best_p2 = p2;
                        best_diff = max_d;
                    }
                }
            }
        }

        if (best_c != -1) {
            z += get_char(best_c);
            curr1 = best_p1;
            curr2 = best_p2;
        } else {
            break; // No more common characters found
        }
    }

    cout << z << "\n";

    return 0;
}