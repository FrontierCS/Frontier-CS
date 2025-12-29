#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <map>
#include <iomanip>

using namespace std;

// Global variables
int N, M;
vector<vector<int>> patterns; // 0=A, 1=C, 2=G, 3=T, 4=?
double total_prob = 0;

// DFS for Principle of Inclusion-Exclusion
// p_idx: current pattern index being considered
// count_in_subset: number of patterns currently included in the subset
// masks: current intersection mask for each position (0-15 representing subset of ACGT)
void dfs_pie(int p_idx, int count_in_subset, vector<int>& masks) {
    if (p_idx == M) {
        if (count_in_subset == 0) return;
        
        double possibilities = 1.0;
        for (int x : masks) {
            int cnt = 0;
            if (x & 1) cnt++;
            if (x & 2) cnt++;
            if (x & 4) cnt++;
            if (x & 8) cnt++;
            
            if (cnt == 0) {
                possibilities = 0;
                break;
            }
            possibilities *= (cnt / 4.0);
        }
        
        if (count_in_subset % 2 == 1) {
            total_prob += possibilities;
        } else {
            total_prob -= possibilities;
        }
        return;
    }

    // Option 1: Don't include pattern p_idx
    dfs_pie(p_idx + 1, count_in_subset, masks);

    // Option 2: Include pattern p_idx
    // Calculate new masks
    vector<int> new_masks = masks;
    bool possible = true;
    for (int j = 0; j < N; ++j) {
        int p_char = patterns[p_idx][j];
        if (p_char != 4) { // Not '?'
            // p_char corresponds to bit p_char
            new_masks[j] &= (1 << p_char);
            if (new_masks[j] == 0) {
                possible = false;
                break;
            }
        }
        // If '?', the mask doesn't restrict further, so remains same
    }

    if (possible) {
        dfs_pie(p_idx + 1, count_in_subset + 1, new_masks);
    }
}

// Memoization for recursive state machine approach
// Key: pair<current_depth, active_pattern_indices>
// Value: probability of matching a suffix of length N-depth
map<pair<int, vector<int>>, double> memo_depth;

// Filter dominated patterns
// Removes pattern i if there exists pattern j (j != i) such that j covers i on the suffix [depth, N).
// Pattern j covers i if for all k in [depth, N), j[k] == '?' or j[k] == i[k].
// If j covers i, then Set(i) is subset of Set(j), so Union(Set(i), Set(j)) = Set(j).
// We can safely remove i.
vector<int> filter_dominated(int depth, const vector<int>& indices) {
    vector<int> result;
    for (size_t idx1 = 0; idx1 < indices.size(); ++idx1) {
        int i = indices[idx1];
        bool dominated = false;
        for (size_t idx2 = 0; idx2 < indices.size(); ++idx2) {
            if (idx1 == idx2) continue;
            int j = indices[idx2];
            
            bool covers = true;
            bool equal = true;
            for (int k = depth; k < N; ++k) {
                if (patterns[j][k] != 4 && patterns[j][k] != patterns[i][k]) {
                    covers = false;
                    equal = false;
                    break;
                }
                if (patterns[j][k] != patterns[i][k]) {
                    equal = false;
                }
            }
            
            if (covers) {
                // If strictly more general, or equal and j < i (to keep one), discard i
                if (!equal || j < i) {
                    dominated = true;
                    break;
                }
            }
        }
        if (!dominated) {
            result.push_back(i);
        }
    }
    sort(result.begin(), result.end());
    return result;
}

double solve_recursive(int depth, vector<int> current_indices) {
    if (current_indices.empty()) return 0.0;
    if (depth == N) return 1.0;

    // Pruning: if any active pattern is all '?' for the rest, prob is 1.0
    for (int idx : current_indices) {
        bool all_q = true;
        for (int k = depth; k < N; ++k) {
            if (patterns[idx][k] != 4) {
                all_q = false;
                break;
            }
        }
        if (all_q) return 1.0;
    }

    // Memoization check
    pair<int, vector<int>> state = {depth, current_indices};
    if (memo_depth.count(state)) return memo_depth[state];

    double prob = 0;
    // Try building the sequence with A, C, G, T at current position
    for (int c = 0; c < 4; ++c) {
        vector<int> next_indices;
        next_indices.reserve(current_indices.size());
        
        // Filter patterns that match character c at current depth
        for (int idx : current_indices) {
            if (patterns[idx][depth] == 4 || patterns[idx][depth] == c) {
                next_indices.push_back(idx);
            }
        }
        
        if (!next_indices.empty()) {
            prob += 0.25 * solve_recursive(depth + 1, next_indices);
        }
    }
    
    return memo_depth[state] = prob;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    
    vector<string> raw_patterns(M);
    patterns.resize(M, vector<int>(N));

    for (int i = 0; i < M; ++i) {
        cin >> raw_patterns[i];
        for (int j = 0; j < N; ++j) {
            char c = raw_patterns[i][j];
            if (c == 'A') patterns[i][j] = 0;
            else if (c == 'C') patterns[i][j] = 1;
            else if (c == 'G') patterns[i][j] = 2;
            else if (c == 'T') patterns[i][j] = 3;
            else patterns[i][j] = 4;
        }
    }

    // Initial filter to remove redundant patterns
    vector<int> active_indices;
    for(int i = 0; i < M; ++i) active_indices.push_back(i);
    active_indices = filter_dominated(0, active_indices);
    
    // Update global patterns to only include relevant ones
    vector<vector<int>> new_patterns;
    for(int idx : active_indices) {
        new_patterns.push_back(patterns[idx]);
    }
    patterns = new_patterns;
    M = patterns.size();

    cout << fixed << setprecision(10);

    // Heuristic: If M is small, PIE is usually faster and simpler.
    // If M is large, PIE is 2^M, which is too slow.
    // The recursive DP approach works well when N is not too large or there is structure.
    if (M <= 22) {
        vector<int> initial_masks(N, 15); // 1111 binary, all chars allowed
        dfs_pie(0, 0, initial_masks);
        cout << total_prob << endl;
    } else {
        vector<int> indices(M);
        for(int i = 0; i < M; ++i) indices[i] = i;
        double ans = solve_recursive(0, indices);
        cout << ans << endl;
    }

    return 0;
}