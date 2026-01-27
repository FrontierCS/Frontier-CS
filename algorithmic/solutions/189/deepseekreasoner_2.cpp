#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <tuple>

using namespace std;

// Parameters and Constants
const int K = 14; // K-mer size for anchoring
const int BW = 80; // Band width for Banded DP
const int MAX_FULL_DP_CELLS = 6000000; // Switch to Banded DP if cells > 6M
const int MAX_BANDED_LEN = 200000; // Switch to Naive if length > 200K (to check memory/time)

// Input Strings
string S1, S2;
int N, M;

// Output Transcript
string transcript;
// Pre-allocated buffers to reduce allocation overhead
vector<int> dp_buffer; 

// Helper to append characters to transcript
inline void push_n(char c, int n) {
    if (n > 0) transcript.append(n, c);
}

// Naive Heuristic: Directly overwrite (Match) then Insert/Delete remaining
void solve_naive(int r, int c, int n, int m) {
    int common = min(n, m);
    // Prefer Matches as they might have 0 cost, worst case cost 1 (Substitution)
    // D+I cost is 2. So M is locally optimal for approximation.
    push_n('M', common);
    if (n > common) push_n('D', n - common);
    else if (m > common) push_n('I', m - common);
}

// Standard Full DP (Needleman-Wunsch)
void solve_dp(int r, int c, int n, int m) {
    // Flattened DP table
    int cols = m + 1;
    size_t sz = (size_t)(n + 1) * cols;
    if (dp_buffer.size() < sz) dp_buffer.resize(sz);
    int* dp = dp_buffer.data();

    auto idx = [&](int i, int j) { return i * cols + j; };

    // Init
    for (int i = 0; i <= n; i++) dp[idx(i, 0)] = i;
    for (int j = 0; j <= m; j++) dp[idx(0, j)] = j;

    // Fill
    for (int i = 1; i <= n; i++) {
        char ch1 = S1[r + i - 1];
        int prev_row_base = idx(i - 1, 0);
        int curr_row_base = idx(i, 0);
        for (int j = 1; j <= m; j++) {
            char ch2 = S2[c + j - 1];
            int costM = dp[prev_row_base + j - 1] + (ch1 == ch2 ? 0 : 1);
            int costD = dp[prev_row_base + j] + 1;
            int costI = dp[curr_row_base + j - 1] + 1;
            dp[curr_row_base + j] = min({costM, costD, costI});
        }
    }

    // Backtrack
    string chunk;
    chunk.reserve(n + m);
    int i = n, j = m;
    while (i > 0 || j > 0) {
        int cur = dp[idx(i, j)];
        if (i > 0 && j > 0) {
            int cost = (S1[r + i - 1] == S2[c + j - 1] ? 0 : 1);
            if (cur == dp[idx(i - 1, j - 1)] + cost) {
                chunk += 'M'; i--; j--; continue;
            }
        }
        if (i > 0 && cur == dp[idx(i - 1, j)] + 1) {
            chunk += 'D'; i--; continue;
        }
        // Must be Ins
        chunk += 'I'; j--;
    }
    reverse(chunk.begin(), chunk.end());
    transcript += chunk;
}

// Banded DP
void solve_banded(int r, int c, int n, int m) {
    double slope = (double)m / n;
    int width = 2 * BW + 5;
    size_t sz = (size_t)(n + 1) * width;
    if (dp_buffer.size() < sz) dp_buffer.resize(sz);
    int* score = dp_buffer.data();
    
    // Initialize with infinity
    fill(score, score + sz, 1e9);

    auto get_piv = [&](int i) { return (int)(i * slope); };
    auto idx = [&](int i, int local) { return i * width + local; };

    // Base case
    int start_piv = get_piv(0);
    int start_loc = 0 - start_piv + BW;
    if (start_loc >= 0 && start_loc < width) score[idx(0, start_loc)] = 0;

    for (int i = 0; i <= n; i++) {
        int piv = get_piv(i);
        int min_j = max(0, piv - BW);
        int max_j = min(m, piv + BW);

        for (int j = min_j; j <= max_j; j++) {
            int loc = j - piv + BW;
            if (loc < 0 || loc >= width) continue;
            int val = score[idx(i, loc)];
            if (val > 5e8) continue;

            // Match/Sub -> (i+1, j+1)
            if (i < n && j < m) {
                int cost = (S1[r + i] == S2[c + j] ? 0 : 1);
                int n_piv = get_piv(i + 1);
                int n_loc = (j + 1) - n_piv + BW;
                if (n_loc >= 0 && n_loc < width) {
                    int& dest = score[idx(i + 1, n_loc)];
                     dest = min(dest, val + cost);
                }
            }
            // Del -> (i+1, j)
            if (i < n) {
                int n_piv = get_piv(i + 1);
                int n_loc = j - n_piv + BW;
                if (n_loc >= 0 && n_loc < width) {
                    int& dest = score[idx(i + 1, n_loc)];
                    dest = min(dest, val + 1);
                }
            }
            // Ins -> (i, j+1)
            // Note: Since we iterate j, we can update j+1 in same row i.
            if (j < m) {
                int n_loc = (j + 1) - piv + BW;
                if (n_loc >= 0 && n_loc < width) {
                    int& dest = score[idx(i, n_loc)];
                    dest = min(dest, val + 1);
                }
            }
        }
    }

    // Check if end is reachable
    int end_piv = get_piv(n);
    int end_loc = m - end_piv + BW;
    if (end_loc < 0 || end_loc >= width || score[idx(n, end_loc)] > 5e8) {
        solve_naive(r, c, n, m);
        return;
    }

    // Backtrack Banded
    string chunk;
    chunk.reserve(n + m);
    int i = n, j = m;
    while (i > 0 || j > 0) {
        int piv = get_piv(i);
        int loc = j - piv + BW;
        int cur = score[idx(i, loc)];

        bool moved = false;
        // From Diag (Match/Sub)
        if (i > 0 && j > 0) {
            int p_piv = get_piv(i - 1);
            int p_loc = (j - 1) - p_piv + BW;
            if (p_loc >= 0 && p_loc < width) {
                int cost = (S1[r + i - 1] == S2[c + j - 1] ? 0 : 1);
                if (score[idx(i - 1, p_loc)] + cost == cur) {
                    chunk += 'M'; i--; j--; moved = true;
                }
            }
        }
        if (moved) continue;

        // From Del (i-1, j)
        if (i > 0) {
            int p_piv = get_piv(i - 1);
            int p_loc = j - p_piv + BW;
            if (p_loc >= 0 && p_loc < width) {
                if (score[idx(i - 1, p_loc)] + 1 == cur) {
                    chunk += 'D'; i--; moved = true;
                }
            }
        }
        if (moved) continue;

        // From Ins (i, j-1)
        if (j > 0) {
            int p_loc = (j - 1) - piv + BW;
            if (p_loc >= 0 && p_loc < width) {
                if (score[idx(i, p_loc)] + 1 == cur) {
                    chunk += 'I'; j--; moved = true;
                }
            }
        }
        if (!moved) break; // Should not happen
    }
    reverse(chunk.begin(), chunk.end());
    transcript += chunk;
}

// Logic to solve a specific rectangular sub-problem
void solve_chunk(int r, int c, int n, int m) {
    if (n == 0 && m == 0) return;

    // Prune matching prefix
    int p = 0;
    while (p < n && p < m && S1[r + p] == S2[c + p]) p++;
    if (p > 0) {
        push_n('M', p);
        r += p; c += p; n -= p; m -= p;
    }
    if (n == 0) { push_n('I', m); return; }
    if (m == 0) { push_n('D', n); return; }

    long long size = (long long)n * m;
    if (size <= MAX_FULL_DP_CELLS) {
        solve_dp(r, c, n, m);
    } else if (n <= MAX_BANDED_LEN) {
        solve_banded(r, c, n, m);
    } else {
        solve_naive(r, c, n, m);
    }
}

struct Candidate {
    int r, c;
};

struct Block {
    int r, c, len;
};

int main() {
    // Fast IO
    ios::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> S1 >> S2)) return 0;
    N = S1.length();
    M = S2.length();
    transcript.reserve(N + M + 1000);

    // If small enough, just solve directly
    if ((long long)N * M <= MAX_FULL_DP_CELLS) {
        solve_dp(0, 0, N, M);
        cout << transcript << endl;
        return 0;
    }

    // --- Anchoring Strategy --- //

    // 1. Hash S2 K-mers
    vector<pair<uint64_t, int>> h2;
    if (M >= K) {
        h2.reserve(M - K + 1);
        uint64_t H = 0, P = 1;
        const uint64_t B = 131; // Prime base
        for (int i = 0; i < K; i++) {
            H = H * B + S2[i];
            if (i > 0) P *= B;
        }
        h2.push_back({H, 0});
        for (int i = K; i < M; i++) {
            H = (H - S2[i - K] * P) * B + S2[i];
            h2.push_back({H, i - K + 1});
        }
        sort(h2.begin(), h2.end());
    }

    // 2. Identify Unique K-mers in S2
    vector<pair<uint64_t, int>> u2;
    u2.reserve(h2.size());
    for (size_t i = 0; i < h2.size(); ) {
        size_t j = i + 1;
        while (j < h2.size() && h2[j].first == h2[i].first) j++;
        if (j == i + 1) { // Occurs exactly once
            u2.push_back(h2[i]);
        }
        i = j;
    }
    h2.clear(); h2.shrink_to_fit();

    // 3. Scan S1 for matching unique K-mers
    vector<Candidate> cands;
    if (N >= K && !u2.empty()) {
        uint64_t H = 0, P = 1;
        const uint64_t B = 131;
        for (int i = 0; i < K; i++) {
            H = H * B + S1[i];
            if (i > 0) P *= B;
        }

        auto check = [&](uint64_t val, int r_idx) {
            auto it = lower_bound(u2.begin(), u2.end(), make_pair(val, -1));
            if (it != u2.end() && it->first == val) {
                cands.push_back({r_idx, it->second});
            }
        };

        check(H, 0);
        for (int i = K; i < N; i++) {
            H = (H - S1[i - K] * P) * B + S1[i];
            check(H, i - K + 1);
        }
    }
    u2.clear(); u2.shrink_to_fit();

    // 4. LIS to find consistent chain of anchors
    // Candidates are naturally ordered by S1 index (r).
    // We need Longest Increasing Subsequence of S2 indices (c).
    vector<int> tails; 
    vector<int> parent(cands.size(), -1);
    vector<int> tail_idxs; // tail_idxs[k] = index in cands of end of chain length k+1

    for (int i = 0; i < (int)cands.size(); i++) {
        int c_val = cands[i].c;
        auto it = lower_bound(tails.begin(), tails.end(), c_val);
        int len = distance(tails.begin(), it);
        if (it == tails.end()) {
            tails.push_back(c_val);
            tail_idxs.push_back(i);
        } else {
            *it = c_val;
            tail_idxs[len] = i;
        }
        if (len > 0) parent[i] = tail_idxs[len - 1];
    }

    // 5. Reconstruct Blocks
    vector<Block> blocks;
    if (!tail_idxs.empty()) {
        int curr = tail_idxs.back();
        while (curr != -1) {
            blocks.push_back({cands[curr].r, cands[curr].c, K});
            curr = parent[curr];
        }
        reverse(blocks.begin(), blocks.end());
    }

    // 6. Merge overlapping blocks
    vector<Block> merged;
    for (auto &b : blocks) {
        if (merged.empty()) {
            merged.push_back(b);
        } else {
            Block &last = merged.back();
            // If current block starts inside previous block
            if (b.r < last.r + last.len) {
                int shift = (last.r + last.len) - b.r;
                // Adjust current block to start after last
                b.r += shift;
                b.c += shift;
                b.len -= shift;
            }
            if (b.len > 0) merged.push_back(b);
        }
    }

    // 7. Solve gaps and append blocks
    int cur_r = 0, cur_c = 0;
    for (auto &b : merged) {
        solve_chunk(cur_r, cur_c, b.r - cur_r, b.c - cur_c);
        push_n('M', b.len);
        cur_r = b.r + b.len;
        cur_c = b.c + b.len;
    }
    // Final gap
    solve_chunk(cur_r, cur_c, N - cur_r, M - cur_c);

    cout << transcript << endl;

    return 0;
}