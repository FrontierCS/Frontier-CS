#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

int main() {
    fast_io();

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    int n = s1.length();
    int m = s2.length();

    string res;
    // Reserve memory to avoid multiple reallocations
    res.reserve(max(n, m) + 100000);

    int i = 0, j = 0;
    
    // Heuristic Parameters
    const int SMALL_WIN = 6;      // Range for local sync search (edit distance lookahead)
    const int LARGE_WIN = 200;    // Range for long jump search (block insert/delete)
    const int LCP_LIMIT = 10;     // Max length to check for Longest Common Prefix
    const int SKIP_STEP = 15;     // Skip long scans for this many steps after a failure
    
    int next_long_scan_i = 0;

    while (i < n || j < m) {
        // 1. Consume immediate matches
        if (i < n && j < m && s1[i] == s2[j]) {
            res += 'M';
            i++;
            j++;
            continue;
        }

        // 2. Handle trailing parts
        if (i == n) {
            // Only s2 remains -> Insertions
            res += 'I';
            j++;
            continue;
        }
        if (j == m) {
            // Only s1 remains -> Deletions
            res += 'D';
            i++;
            continue;
        }

        // 3. Heuristic Search
        // Search for a sync point (u, v) such that s1[i+u] == s2[j+v]
        // maximizing a heuristic score based on LCP and cost.
        
        int best_u = -1, best_v = -1;
        int max_score = -1000000;

        // Local search in small window
        for (int u = 0; u <= SMALL_WIN && i + u < n; u++) {
            for (int v = 0; v <= SMALL_WIN && j + v < m; v++) {
                if (u == 0 && v == 0) continue;
                
                if (s1[i + u] == s2[j + v]) {
                    // Calculate LCP roughly
                    int lcp = 0;
                    while (lcp < LCP_LIMIT && i + u + lcp < n && j + v + lcp < m && 
                           s1[i + u + lcp] == s2[j + v + lcp]) {
                        lcp++;
                    }
                    
                    // Cost approx: max(u, v) is roughly the edits needed to traverse (u, v)
                    // Score: Reward LCP, penalize Cost.
                    int cost = (u > v) ? u : v;
                    int score = lcp * 4 - cost * 2; 
                    
                    if (score > max_score) {
                        max_score = score;
                        best_u = u;
                        best_v = v;
                    }
                }
            }
        }

        // Threshold to accept a local match. 
        // A score >= -2 means we found something reasonable (e.g. cost 1 with lcp 0, or cost 2 with lcp 1).
        bool found_good = (max_score >= -2); 

        // If local search fails, try a wider scan for block Insert/Delete
        if (!found_good && i >= next_long_scan_i) {
            int best_long_dist = 1000000;
            int long_u = -1, long_v = -1;
            
            // Look for S1's next 3-mer in S2 (implies Insertions)
            if (i + 3 < n) {
                char c0 = s1[i], c1 = s1[i+1], c2 = s1[i+2];
                // Limit search
                int limit = min(m, j + LARGE_WIN);
                for (int v = SMALL_WIN + 1; j + v + 2 < limit; v++) {
                    if (s2[j+v] == c0 && s2[j+v+1] == c1 && s2[j+v+2] == c2) {
                        int cost = v; 
                        if (cost < best_long_dist) {
                            best_long_dist = cost;
                            long_u = 0;
                            long_v = v;
                        }
                        break; // Found closest
                    }
                }
            }

            // Look for S2's next 3-mer in S1 (implies Deletions)
            if (j + 3 < m) {
                char c0 = s2[j], c1 = s2[j+1], c2 = s2[j+2];
                int limit = min(n, i + LARGE_WIN);
                for (int u = SMALL_WIN + 1; i + u + 2 < limit; u++) {
                    if (s1[i+u] == c0 && s1[i+u+1] == c1 && s1[i+u+2] == c2) {
                        int cost = u; 
                        if (cost < best_long_dist) {
                            best_long_dist = cost;
                            long_u = u;
                            long_v = 0;
                        }
                        break;
                    }
                }
            }

            if (long_u != -1) {
                best_u = long_u;
                best_v = long_v;
                found_good = true;
            } else {
                // If failed, do not scan again for a while to save time
                next_long_scan_i = i + SKIP_STEP;
            }
        }

        // 4. Execute move
        if (found_good) {
            int u = best_u;
            int v = best_v;
            
            // To reach (u, v), we perform a mix of Matches (Substitute) and Ins/Dels.
            // Heuristic: Move diagonally as much as possible ('M'), then fill gaps.
            // This assumes the diagonal path (Subs) is generally preferred or equal to indels locally,
            // or simply gets us closer to the sync point.
            while (u > 0 && v > 0) {
                res += 'M';
                i++; j++;
                u--; v--;
            }
            while (u > 0) {
                res += 'D';
                i++;
                u--;
            }
            while (v > 0) {
                res += 'I';
                j++;
                v--;
            }
        } else {
            // Fallback: Just Substitute ('M') and move forward.
            // This maintains the diagonal alignment, which is often correct for noisy regions.
            res += 'M';
            i++;
            j++;
        }
    }

    cout << res << endl;

    return 0;
}