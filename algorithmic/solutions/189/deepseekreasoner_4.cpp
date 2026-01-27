#include <iostream>
#include <vector>
#include <string>
#include <string_view>
#include <algorithm>

using namespace std;

// Function for fast I/O setup
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

int main() {
    fast_io();

    string s1_str, s2_str;
    if (!(cin >> s1_str >> s2_str)) return 0;
    
    // Use string_view to avoid copying substrings (O(1) creation)
    string_view s1(s1_str);
    string_view s2(s2_str);

    size_t n = s1.size();
    size_t m = s2.size();
    size_t i = 0;
    size_t j = 0;

    string res;
    // Pre-allocate memory to prevent resizing overhead
    // Worst case length is N + M
    res.reserve(n + m);

    // Heuristic Parameters
    // SHORT_LOOK: How far to check for simple insertions/deletions on mismatch
    const int SHORT_LOOK = 50; 
    // CHECK_LEN: Length of substring match required to consider strings "re-synchronized"
    const int CHECK_LEN = 12;      
    // LONG_LOOK_LIMIT: Range for long-distance sync search
    const int LONG_LOOK_LIMIT = 5000;
    // LONG_SEARCH_INTERVAL: Only perform expensive search after this many failures to find sync
    const int LONG_SEARCH_INTERVAL = 100; 
    
    int failed_sync_counter = 0;

    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            res += 'M';
            i++;
            j++;
            // If we match, we are currently synced
            failed_sync_counter = 0;
        } else {
            bool found = false;
            int best_k = -1;
            char type = ' '; 

            // 1. Short Lookahead
            // Check if jumping ahead a few chars (Delete) or inserting a few chars (Insert)
            // allows us to match the current characters.
            for (int k = 1; k <= SHORT_LOOK; ++k) {
                // Check Delete from S1 (skip k in S1, align s1[i+k] with s2[j])
                bool del_match = false;
                if (i + k < n) {
                    // Fast check first char before full substring compare
                    if (s1[i+k] == s2[j]) {
                        size_t len = min((size_t)CHECK_LEN, n - (i + k));
                        // Ensure comparison stays within bounds of S2 as well
                        if (j + len <= m) {    
                            if (s1.substr(i+k, len) == s2.substr(j, len)) {
                                del_match = true;
                            }
                        }
                    }
                }
                
                if (del_match) {
                    best_k = k; type = 'D'; break; // Prefer smallest k
                }

                // Check Insert into S1 (skip k in S2, align s1[i] with s2[j+k])
                bool ins_match = false;
                if (j + k < m) {
                    if (s1[i] == s2[j+k]) {
                        size_t len = min((size_t)CHECK_LEN, m - (j + k));
                        // Ensure comparison stays within bounds of S1
                        if (i + len <= n) {
                            if (s1.substr(i, len) == s2.substr(j+k, len)) {
                                ins_match = true;
                            }
                        }
                    }
                }

                if (ins_match) {
                    best_k = k; type = 'I'; break;
                }
            }

            if (best_k != -1) {
                if (type == 'D') {
                    res.append(best_k, 'D');
                    i += best_k;
                } else {
                    res.append(best_k, 'I');
                    j += best_k;
                }
                found = true;
                failed_sync_counter = 0;
            }

            // 2. Long Search
            // If short lookahead failed repeatedly, assume we might have a larger gap (block insert/delete).
            // Search a larger window using optimized string search.
            if (!found && failed_sync_counter >= LONG_SEARCH_INTERVAL) {
                size_t limit_s1 = min(n, i + LONG_LOOK_LIMIT);
                size_t limit_s2 = min(m, j + LONG_LOOK_LIMIT);
                
                // Only search if we have enough characters for a reliable key
                if (i + CHECK_LEN <= n && j + CHECK_LEN <= m) {
                    // Try to find S1's current block in the upcoming window of S2
                    string_view key1 = s1.substr(i, CHECK_LEN);
                    string_view search_area2 = s2.substr(j, limit_s2 - j);
                    
                    size_t pos2 = search_area2.find(key1);
                    
                    // Try to find S2's current block in the upcoming window of S1
                    string_view key2 = s2.substr(j, CHECK_LEN);
                    string_view search_area1 = s1.substr(i, limit_s1 - i);
                    
                    size_t pos1 = search_area1.find(key2);
                    
                    size_t dist_ins = (pos2 == string_view::npos) ? 1e9 : pos2;
                    size_t dist_del = (pos1 == string_view::npos) ? 1e9 : pos1;
                    
                    if (dist_ins < 1e9 || dist_del < 1e9) {
                        found = true;
                        if (dist_del < dist_ins) {
                            // Deletion path is shorter
                            res.append(dist_del, 'D');
                            i += dist_del;
                        } else {
                            // Insertion path is shorter
                            res.append(dist_ins, 'I');
                            j += dist_ins;
                        }
                        failed_sync_counter = 0;
                    }
                }
                // Reset counter to wait before next expensive search if this one failed
                if (!found) failed_sync_counter = 0; 
            }

            // 3. Fallback
            // If no strategies worked, assume substitution (or noise).
            // Output 'M' (cost 1 if mismatched) to advance both pointers diagonally.
            // This prevents desynchronization accumulation.
            if (!found) {
                res += 'M';
                i++;
                j++;
                failed_sync_counter++;
            }
        }
    }

    // Handle remaining tails
    if (i < n) res.append(n - i, 'D');
    if (j < m) res.append(m - j, 'I');

    cout << res << endl;
    return 0;
}