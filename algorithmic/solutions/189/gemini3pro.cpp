#include <iostream>
#include <string>
#include <vector>
#include <algorithm>
#include <chrono>

using namespace std;

// Fast I/O configuration
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

int main() {
    fast_io();

    string s1, s2;
    if (!(cin >> s1 >> s2)) return 0;

    const int n = s1.length();
    const int m = s2.length();

    // Reserve memory for the transcript string to optimize performance
    string res;
    res.reserve(max(n, m) + max(n, m) / 2);

    int p1 = 0;
    int p2 = 0;

    // Parameters for heuristic greedy search
    // W: Lookahead window size. A smaller window is faster but may miss optimal long-distance alignments.
    // K: Anchor length (K-mer). A match of this length is considered a synchronization point.
    const int W = 50; 
    const int K = 5;

    auto start_time = chrono::high_resolution_clock::now();
    bool time_critical = false;

    while (p1 < n && p2 < m) {
        // 1. Opportunistic Match (Greedy)
        // If characters match, consume them immediately.
        if (s1[p1] == s2[p2]) {
            res += 'M';
            p1++;
            p2++;
            continue;
        }

        // Periodic Time Check (approx every 16k ops) to prevent TLE
        if (!time_critical && (p1 & 0x3FFF) == 0) {
            auto current_time = chrono::high_resolution_clock::now();
            auto duration = chrono::duration_cast<chrono::milliseconds>(current_time - start_time).count();
            if (duration > 2800) { // If > 2.8s elapsed, switch to fallback mode
                time_critical = true;
            }
        }

        // Fallback mode: if time is running out, just use substitution/matches to traverse quickly.
        if (time_critical) {
            res += 'M';
            p1++;
            p2++;
            continue;
        }

        // 2. Lookahead for Synchronization (Anchor Search)
        bool found = false;
        
        int rem1 = n - p1;
        int rem2 = m - p2;
        
        // Calculate search limit based on window size and remaining string length.
        // We need at least K characters to check for an anchor.
        int limit = W;
        if (limit > rem1 - K) limit = rem1 - K;
        if (limit > rem2 - K) limit = rem2 - K;

        if (limit < 1) {
            // Not enough characters left for K-mer search, fallback to step-by-step
            res += 'M';
            p1++;
            p2++;
            continue;
        }

        // Search for nearest anchor within the window
        // We prioritize smaller offsets 'k' to minimize the edit distance.
        for (int k = 1; k <= limit; ++k) {
            // A. Check Insertion: S1 matches S2 shifted by k (Gap in S1)
            // Check S1[p1...p1+K-1] vs S2[p2+k...p2+k+K-1]
            bool match_ins = true;
            for(int i=0; i<K; ++i) {
                if(s1[p1+i] != s2[p2+k+i]) { match_ins = false; break; }
            }
            if (match_ins) {
                for(int i=0; i<k; ++i) res += 'I'; // Insert k characters from S2
                p2 += k;
                found = true;
                break;
            }

            // B. Check Deletion: S1 shifted by k matches S2 (Gap in S2)
            // Check S1[p1+k...p1+k+K-1] vs S2[p2...p2+K-1]
            bool match_del = true;
            for(int i=0; i<K; ++i) {
                if(s1[p1+k+i] != s2[p2+i]) { match_del = false; break; }
            }
            if (match_del) {
                for(int i=0; i<k; ++i) res += 'D'; // Delete k characters from S1
                p1 += k;
                found = true;
                break;
            }

            // C. Check Diagonal/Substitution: S1 shifted by k matches S2 shifted by k
            // Check S1[p1+k...p1+k+K-1] vs S2[p2+k...p2+k+K-1]
            bool match_diag = true;
            for(int i=0; i<K; ++i) {
                if(s1[p1+k+i] != s2[p2+k+i]) { match_diag = false; break; }
            }
            if (match_diag) {
                // We found a sync point after skipping k characters in both.
                // Treat the skipped characters as substitutions (or chance matches).
                for(int i=0; i<k; ++i) res += 'M';
                p1 += k;
                p2 += k;
                found = true;
                break;
            }
        }

        if (!found) {
            // No anchor found within window, advance one step assuming substitution
            // This handles localized noise or random mismatches.
            res += 'M';
            p1++;
            p2++;
        }
    }

    // Handle Remaining Suffixes
    // If S1 has leftovers, Delete them.
    while (p1 < n) {
        res += 'D';
        p1++;
    }
    // If S2 has leftovers, Insert them.
    while (p2 < m) {
        res += 'I';
        p2++;
    }

    cout << res << "\n";

    return 0;
}