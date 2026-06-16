#include "testlib.h"
#include <vector>
#include <iostream>
#include <algorithm>
#include <cmath>

using namespace std;

// Struct to represent a contiguous block of identical values
struct Block {
    int value;
    int count;
    int start_idx; // 1-based, inclusive
    int end_idx;   // 1-based, inclusive
};

// Dynamic scoring multipliers (based on k = number of distinct blocks).
// Full score if queries <= C_BASE * k; zero score if queries >= C_ZERO * k.
// Tune these to set how aggressively few-query solutions are rewarded.
const double C_BASE = 1.0;
const double C_ZERO = 12.0;

// Sparse Table resources
// Max N is 200,000, so max distinct blocks is also 200,000.
const int MAX_BLOCKS = 200005;
const int LOG_BLOCKS = 19;     // 2^18 = 262144
int st[MAX_BLOCKS][LOG_BLOCKS];
vector<Block> blocks;

// RMQ Comparator: Prefers higher frequency, then smaller value
int get_best_block_idx(int b1, int b2) {
    if (b1 == -1) return b2;
    if (b2 == -1) return b1;
    if (blocks[b1].count > blocks[b2].count) return b1;
    if (blocks[b2].count > blocks[b1].count) return b2;
    // Tie-break: smaller value (implies smaller block index in sorted array)
    return (b1 < b2) ? b1 : b2;
}

void build_st(int k) {
    for (int i = 0; i < k; ++i) st[i][0] = i;
    for (int j = 1; j < LOG_BLOCKS; ++j) {
        for (int i = 0; i + (1 << j) <= k; ++i) {
            st[i][j] = get_best_block_idx(st[i][j-1], st[i + (1 << (j-1))][j-1]);
        }
    }
}

int query_st(int L, int R) {
    if (L > R) return -1;
    int j = 31 - __builtin_clz(R - L + 1);
    return get_best_block_idx(st[L][j], st[R - (1 << j) + 1][j]);
}

int main(int argc, char* argv[]) {
    setName("Interactor for Omkar and Modes (Dynamic Scoring)");
    registerInteraction(argc, argv);

    double total_ratio = 0.0;
    double total_unbounded_ratio = 0.0;
    int case_count = 0;
    long long total_queries_all = 0;

    // Loop to handle multiple test cases in one file (if present)
    while (!inf.seekEof()) {
        case_count++;
        
        // 1. Read N for the current test case
        int n = inf.readInt(1, 200000, "n");
        
        // 2. Read the sorted array for the current test case
        vector<int> a(n);
        for(int i = 0; i < n; ++i) {
            a[i] = inf.readInt(1, 1000000000, "a_i");
        }

        // 3. Prepare Blocks and RMQ for O(log K) mode queries
        blocks.clear();
        for(int i = 0; i < n; ) {
            int val = a[i];
            int j = i;
            while(j < n && a[j] == val) j++;
            // Create block
            blocks.push_back({val, j - i, i + 1, j}); 
            i = j;
        }
        build_st(blocks.size());

        // 4. Send N to user
        cout << n << endl;

        // 5. Define Dynamic Scoring Limits based on K (number of distinct blocks).
        // k forces solutions to exploit the sorted/mode structure instead of
        // trivially scanning every position (which would take n queries).
        long long k = (long long)blocks.size();
        long long k_base = (long long)(C_BASE * (double)k);
        long long k_zero = (long long)(C_ZERO * (double)k);

        // Safety for very small k
        if (k_base < 1) k_base = 1;
        if (k_zero <= k_base) k_zero = k_base + 1;

        long long queries = 0;
        bool solved = false;
        
        // 6. Interaction Loop
        while(true) {
            string type = ouf.readToken("[?!]");
            if (type == "?") {
                queries++;
                int l = ouf.readInt(1, n, "l");
                int r = ouf.readInt(l, n, "r"); // ensure l <= r in reader

                // Hard limit to stop runaway solutions, slightly above 0-score threshold
                if (queries > k_zero + 100) {
                     cout << -1 << endl;
                     quitf(_wa, "Case %d: Query limit exceeded (>%lld)", case_count, k_zero);
                }

                // --- Solve Query using Blocks + RMQ ---
                // Find block containing l
                auto it_l = lower_bound(blocks.begin(), blocks.end(), l, [](const Block& b, int val){
                    return b.end_idx < val;
                });
                int b_l = distance(blocks.begin(), it_l);

                // Find block containing r
                auto it_r = lower_bound(blocks.begin(), blocks.end(), r, [](const Block& b, int val){
                    return b.end_idx < val;
                });
                int b_r = distance(blocks.begin(), it_r);

                int best_val = -1;
                int best_freq = -1;

                if (b_l == b_r) {
                    // Entire range is inside one block
                    best_val = blocks[b_l].value;
                    best_freq = r - l + 1;
                } else {
                    // Left partial
                    int freq_l = blocks[b_l].end_idx - l + 1;
                    best_val = blocks[b_l].value;
                    best_freq = freq_l;

                    // Right partial
                    int freq_r = r - blocks[b_r].start_idx + 1;
                    if (freq_r > best_freq) {
                        best_freq = freq_r;
                        best_val = blocks[b_r].value;
                    }

                    // Middle full blocks
                    if (b_l + 1 <= b_r - 1) {
                        int b_max_idx = query_st(b_l + 1, b_r - 1);
                        if (b_max_idx != -1) {
                            int freq_mid = blocks[b_max_idx].count;
                            int val_mid = blocks[b_max_idx].value;
                            
                            if (freq_mid > best_freq) {
                                best_freq = freq_mid;
                                best_val = val_mid;
                            } else if (freq_mid == best_freq) {
                                // Tie-break: smallest value
                                if (val_mid < best_val) best_val = val_mid;
                            }
                        }
                    }
                }
                cout << best_val << " " << best_freq << endl;

            } else {
                // Type is "!", read user answer
                vector<int> user_ans(n);
                for(int i=0; i<n; ++i) {
                    user_ans[i] = ouf.readInt();
                }
                
                if (user_ans == a) {
                    solved = true;
                } else {
                    quitf(_wa, "Case %d: Incorrect array restored.", case_count);
                }
                break; // End of this test case
            }
        }
        
        total_queries_all += queries;

        // 7. Calculate Independent Score for this Case
        double current_ratio = 0.0;
        double current_unbounded = 0.0;
        
        if (solved) {
            // Single unbounded quadratic scoring curve in the query count:
            //   r = 1.0  when queries == k_base   (-> 100 after the judge's *100)
            //   r = 0.0  when queries == k_zero
            //   r > 1.0  when queries <  k_base   (unbounded: rewards extra-efficient
            //                                      solutions with a score above 100)
            // Clamp r at 0 from below so the parabola does not turn back upward once
            // queries exceed k_zero (and so the value stays >= 0 for the judge regex).
            double r = (double)(k_zero - queries) / (double)(k_zero - k_base);
            if (r < 0.0) r = 0.0;
            double curve = r * r;

            // Unbounded score: report the raw curve (may exceed 1 -> scoreUnbounded > 100).
            current_unbounded = curve;

            // Bounded score: same curve clipped to 1.0, i.e. clipped to 100 on output.
            current_ratio = (curve > 1.0) ? 1.0 : curve;
        } else {
            // Not solved (or WA, though WA usually quits immediately above)
            current_ratio = 0.0;
            current_unbounded = 0.0;
        }

        total_ratio += current_ratio;
        total_unbounded_ratio += current_unbounded;
    }

    if (case_count == 0) {
        quitf(_fail, "No test cases found in input.");
    }

    // 8. Average the scores
    double final_unbounded = total_unbounded_ratio / case_count;

    // Bounded score is the unbounded average clipped to 100 (i.e. ratio clipped to 1.0).
    double final_score_ratio = total_ratio / case_count;
    if (final_score_ratio > 1.0) final_score_ratio = 1.0;
    if (final_score_ratio < 0.0) final_score_ratio = 0.0;

    // Output formatted exactly as requested
    quitp(final_score_ratio, "Queries: %lld. Ratio: %.4f, RatioUnbounded: %.4f",
          total_queries_all, final_score_ratio, final_unbounded);

    return 0;
}