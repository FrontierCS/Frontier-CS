#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <iomanip>

using namespace std;

// Global variables to store problem data and DP states
int N, M;
vector<string> patterns;

struct SuffixInfo {
    int id;
    char first_char;
    int next_id;
    bool is_wild;
};

// suffixes[j] contains unique suffix identifiers for suffixes starting at index j
vector<vector<SuffixInfo>> suffixes;
// Maps original pattern index and level to the unique suffix ID
vector<vector<int>> pattern_id_at_level;
// dominates[j][u][v] is true if suffix ID u at level j covers suffix ID v
vector<vector<vector<bool>>> dominates;
// Memoization for DP: maps sorted list of active IDs to probability
vector<map<vector<int>, double>> memo;

// Recursive function with memoization
double solve(int level, vector<int> active_ids) {
    if (active_ids.empty()) return 0.0;

    // Prune dominated IDs
    // If ID u dominates ID v, then the set of strings matching u includes
    // all strings matching v. Thus, v is redundant for the union.
    vector<int> filtered_ids;
    filtered_ids.reserve(active_ids.size());

    for (size_t i = 0; i < active_ids.size(); ++i) {
        bool is_dominated = false;
        for (size_t j = 0; j < active_ids.size(); ++j) {
            if (i == j) continue;
            // Check if j dominates i
            if (dominates[level][active_ids[j]][active_ids[i]]) {
                is_dominated = true;
                break;
            }
        }
        if (!is_dominated) {
            filtered_ids.push_back(active_ids[i]);
        }
    }
    active_ids = filtered_ids;

    // Optimization: If any active pattern is a full wildcard match for the remainder, probability is 1.0
    for (int id : active_ids) {
        if (suffixes[level][id].is_wild) return 1.0;
    }

    if (level == N) return 1.0;

    // Check memoization
    if (memo[level].count(active_ids)) return memo[level][active_ids];

    double prob = 0.0;
    char chars[] = {'A', 'C', 'G', 'T'};

    // Try extending with each possible character
    for (char c : chars) {
        vector<int> next_ids;
        for (int id : active_ids) {
            char p = suffixes[level][id].first_char;
            // Pattern matches char c if it has '?' or exactly c
            if (p == '?' || p == c) {
                next_ids.push_back(suffixes[level][id].next_id);
            }
        }
        // Canonicalize the list of next IDs
        sort(next_ids.begin(), next_ids.end());
        next_ids.erase(unique(next_ids.begin(), next_ids.end()), next_ids.end());

        if (!next_ids.empty()) {
            prob += 0.25 * solve(level + 1, next_ids);
        }
    }

    return memo[level][active_ids] = prob;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    patterns.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> patterns[i];
    }

    // Initialize data structures
    suffixes.resize(N + 1);
    pattern_id_at_level.assign(M, vector<int>(N + 1));
    dominates.resize(N + 1);
    memo.resize(N + 1);

    // Base case: at level N, there is only one empty suffix (ID 0)
    suffixes[N].push_back({0, 0, -1, true});
    for(int i = 0; i < M; ++i) pattern_id_at_level[i][N] = 0;
    dominates[N].resize(1, vector<bool>(1, true));

    // Build unique suffixes and dominance relations from N-1 down to 0
    for (int j = N - 1; j >= 0; --j) {
        map<pair<char, int>, int> lookup;
        
        for (int i = 0; i < M; ++i) {
            char c = patterns[i][j];
            int n_id = pattern_id_at_level[i][j+1];
            
            // Identify unique suffix by (char, next_suffix_id)
            if (lookup.find({c, n_id}) == lookup.end()) {
                int new_id = (int)suffixes[j].size();
                SuffixInfo info;
                info.id = new_id;
                info.first_char = c;
                info.next_id = n_id;
                // A suffix is wild if current char is '?' and the rest is also wild
                info.is_wild = (c == '?') && suffixes[j+1][n_id].is_wild;
                suffixes[j].push_back(info);
                lookup[{c, n_id}] = new_id;
            }
            pattern_id_at_level[i][j] = lookup[{c, n_id}];
        }
        
        // Compute dominance for this level
        // u covers v if u matches a superset of strings that v matches
        int cnt = suffixes[j].size();
        dominates[j].assign(cnt, vector<bool>(cnt, false));
        for (int u = 0; u < cnt; ++u) {
            for (int v = 0; v < cnt; ++v) {
                if (u == v) {
                    dominates[j][u][v] = true; 
                    continue;
                }
                char cu = suffixes[j][u].first_char;
                char cv = suffixes[j][v].first_char;
                
                // For u to cover v, the first character must allow covering
                // '?' covers '?' and 'A','C','G','T'
                // 'A' covers 'A', but not '?'
                bool match = (cu == '?' || cu == cv);
                if (match) {
                    // And the rest of the suffix must also cover
                    if (dominates[j+1][suffixes[j][u].next_id][suffixes[j][v].next_id]) {
                        dominates[j][u][v] = true;
                    }
                }
            }
        }
    }

    // Initial active IDs at level 0
    vector<int> initial_ids;
    for (int i = 0; i < M; ++i) initial_ids.push_back(pattern_id_at_level[i][0]);
    sort(initial_ids.begin(), initial_ids.end());
    initial_ids.erase(unique(initial_ids.begin(), initial_ids.end()), initial_ids.end());

    cout << fixed << setprecision(10) << solve(0, initial_ids) << endl;

    return 0;
}