#include <iostream>
#include <string>
#include <algorithm>
#include <vector>

using namespace std;

// Speed up C++ I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

int main() {
    fast_io();

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = (int)s1.length();
    int m = (int)s2.length();

    // Reserve memory reasonably to avoid multiple reallocations
    // Max length is N+M (delete all then insert all), though likely smaller.
    string res;
    res.reserve(max(n, m) + min(n, m) / 2);

    int i = 0;
    int j = 0;

    // Heuristic parameters
    // MAX_LOOKAHEAD: Checks small gaps for local noise (insertions/deletions/typos).
    const int MAX_LOOKAHEAD = 50; 
    // MATCH_LEN: Required length of matching substring to confirm a synchronization point.
    // Higher prevents false positives on random character matches.
    const int MATCH_LEN = 5;

    while (i < n && j < m) {
        // 1. Greedy Match: Always consume matching characters (Cost 0)
        if (s1[i] == s2[j]) {
            res += 'M';
            i++;
            j++;
            continue;
        }

        // Mismatch found at s1[i] vs s2[j].
        // Strategies: Substitute ('M'), specific Delete ('D'), specific Insert ('I').
        
        int best_k = -1;
        char best_type = ' '; // 'D' or 'I'
        bool found = false;

        // 2. Search for a local synchronization point within MAX_LOOKAHEAD
        // We prefer smaller k (lower cost).
        for (int k = 1; k <= MAX_LOOKAHEAD; ++k) {
            // Check Deletion: Skip k characters in s1. Align s1[i+k] with s2[j].
            // Candidates: s1[i+k...i+k+len] == s2[j...j+len]
            if (i + k < n) {
                // Quick check first character to minimize overhead
                if (s1[i + k] == s2[j]) {
                    // Check block match
                    bool match = true;
                    int len_check = MATCH_LEN;
                    // Adjust check length near end of strings
                    if (i + k + len_check > n) len_check = n - (i + k);
                    if (j + len_check > m) len_check = m - j;

                    if (len_check > 0) {
                        for (int l = 1; l < len_check; ++l) {
                            if (s1[i + k + l] != s2[j + l]) {
                                match = false;
                                break;
                            }
                        }
                    } else {
                        match = false;
                    }

                    if (match) {
                        best_k = k;
                        best_type = 'D';
                        found = true;
                        break; // Found smallest k
                    }
                }
            }

            // Check Insertion: Skip k characters in s2. Align s1[i] with s2[j+k].
            // Candidates: s1[i...i+len] == s2[j+k...j+k+len]
            if (j + k < m) {
                if (s1[i] == s2[j + k]) {
                    bool match = true;
                    int len_check = MATCH_LEN;
                    if (i + len_check > n) len_check = n - i;
                    if (j + k + len_check > m) len_check = m - (j + k);

                    if (len_check > 0) {
                        for (int l = 1; l < len_check; ++l) {
                            if (s1[i + l] != s2[j + k + l]) {
                                match = false;
                                break;
                            }
                        }
                    } else {
                         match = false;
                    }

                    if (match) {
                        best_k = k;
                        best_type = 'I';
                        found = true;
                        break; // Found smallest k
                    }
                }
            }
        }

        // 3. Global Length Heuristic
        // If local search fails, check if a massive block insert/delete aligns the remainders.
        // This handles cases where one string is much longer due to a large insertion.
        if (!found) {
            int diff = (n - i) - (m - j); // If > 0, S1 is longer -> try deleting from S1
            
            if (diff > 0) {
                int k = diff;
                // Only check if k is significant and valid, and wasn't checked above
                if (k > MAX_LOOKAHEAD && (i + k < n)) {
                    if (s1[i + k] == s2[j]) {
                        bool match = true;
                        int len_check = MATCH_LEN;
                        if (i + k + len_check > n) len_check = n - (i + k);
                        if (j + len_check > m) len_check = m - j;

                        if (len_check > 0) {
                            for (int l = 1; l < len_check; ++l) {
                                if (s1[i + k + l] != s2[j + l]) {
                                    match = false;
                                    break;
                                }
                            }
                        } else match = false;

                        if (match) {
                            best_k = k;
                            best_type = 'D';
                            found = true;
                        }
                    }
                }
            } else if (diff < 0) {
                int k = -diff; // Insert k into S1 (consume k from S2)
                if (k > MAX_LOOKAHEAD && (j + k < m)) {
                    if (s1[i] == s2[j + k]) {
                        bool match = true;
                        int len_check = MATCH_LEN;
                        if (i + len_check > n) len_check = n - i;
                        if (j + k + len_check > m) len_check = m - (j + k);

                        if (len_check > 0) {
                            for (int l = 1; l < len_check; ++l) {
                                if (s1[i + l] != s2[j + k + l]) {
                                    match = false;
                                    break;
                                }
                            }
                        } else match = false;

                        if (match) {
                            best_k = k;
                            best_type = 'I';
                            found = true;
                        }
                    }
                }
            }
        }

        // Apply best move
        if (found) {
            if (best_type == 'D') {
                for (int d = 0; d < best_k; ++d) res += 'D';
                i += best_k;
            } else {
                for (int ins = 0; ins < best_k; ++ins) res += 'I';
                j += best_k;
            }
        } else {
            // No sync found: perform substitution (Match with cost 1) and advance
            // This is safer than random large inserts/deletes.
            res += 'M';
            i++;
            j++;
        }
    }

    // Append remaining characters
    while (i < n) {
        res += 'D';
        i++;
    }
    while (j < m) {
        res += 'I';
        j++;
    }

    cout << res << "\n";

    return 0;
}