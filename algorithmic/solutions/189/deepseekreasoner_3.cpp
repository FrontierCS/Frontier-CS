#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

// --- Parameters ---
const int K = 25; // Anchor length
const int STEP_S2 = 25; // Sampling step for S2 indexing
const long long DP_LIMIT = 5000000; // Max cells for exact DP

// --- Segment Structure ---
struct Segment {
    int i, j, len;
    int id;
};

// --- Rolling Hash ---
typedef unsigned long long ULL;
const ULL BASE = 131;

// --- Fenwick Tree for LIS ---
vector<pair<int, int>> bit_tree;
int bit_n;

void bit_init(int n) {
    bit_n = n;
    bit_tree.assign(n + 1, {0, -1});
}

pair<int, int> bit_query(int idx) {
    pair<int, int> res = {0, -1};
    // BIT stores prefix max, standard implementation
    for (; idx > 0; idx -= idx & -idx) {
        if (bit_tree[idx].first > res.first) {
            res = bit_tree[idx];
        }
    }
    return res;
}

void bit_update(int idx, pair<int, int> val) {
    // Updates point and propagates up
    for (; idx <= bit_n; idx += idx & -idx) {
        if (val.first > bit_tree[idx].first) {
            bit_tree[idx] = val;
        }
    }
}

// --- Exact DP ---
string solve_dp(const string& s1, const string& s2) {
    int n = s1.size();
    int m = s2.size();
    
    // path[i][j]: 0: match/sub, 1: del(from s1, up), 2: ins(from s2, left)
    vector<vector<unsigned char>> path(n + 1, vector<unsigned char>(m + 1)); 
    
    // DP Costs: we only need two rows to compute, but path needs full table.
    vector<int> prev(m + 1), curr(m + 1);
    
    for (int j = 0; j <= m; ++j) {
        prev[j] = j;
        path[0][j] = 2; // Insert
    }
    
    for (int i = 1; i <= n; ++i) {
        curr[0] = i;
        path[i][0] = 1; // Delete
        for (int j = 1; j <= m; ++j) {
            int cost_match = prev[j-1] + (s1[i-1] == s2[j-1] ? 0 : 1);
            int cost_del = prev[j] + 1;
            int cost_ins = curr[j-1] + 1;
            
            if (cost_match <= cost_del && cost_match <= cost_ins) {
                curr[j] = cost_match;
                path[i][j] = 0;
            } else if (cost_del <= cost_ins) {
                curr[j] = cost_del;
                path[i][j] = 1;
            } else {
                curr[j] = cost_ins;
                path[i][j] = 2;
            }
        }
        prev = curr;
    }
    
    // Reconstruct
    string res;
    res.reserve(n + m);
    int i = n, j = m;
    while (i > 0 || j > 0) {
        if (i > 0 && j > 0 && path[i][j] == 0) {
            res += 'M';
            i--; j--;
        } else if (i > 0 && path[i][j] == 1) {
            res += 'D';
            i--;
        } else {
            res += 'I';
            j--;
        }
    }
    reverse(res.begin(), res.end());
    return res;
}

string simple_heuristic(const string& s1, const string& s2) {
    int n = s1.size();
    int m = s2.size();
    string res = "";
    int min_len = min(n, m);
    // Prefer matching/substitution on diagonal
    for (int k = 0; k < min_len; ++k) res += 'M';
    if (n > min_len) for (int k = min_len; k < n; ++k) res += 'D';
    if (m > min_len) for (int k = min_len; k < m; ++k) res += 'I';
    return res;
}

// --- Main Solver ---
int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string S1, S2;
    if (!(cin >> S1 >> S2)) return 0;
    
    int N = S1.length();
    int M = S2.length();

    if (N == 0) {
        for (int i = 0; i < M; ++i) cout << 'I';
        cout << endl;
        return 0;
    }
    if (M == 0) {
        for (int i = 0; i < N; ++i) cout << 'D';
        cout << endl;
        return 0;
    }

    // 1. Build Index on S2
    struct HashNode {
        int pos;
        int next;
    };
    const int HASH_SIZE = 1 << 20;
    const int HASH_MASK = HASH_SIZE - 1;
    vector<int> head(HASH_SIZE, -1);
    vector<HashNode> nodes;
    nodes.reserve(M / STEP_S2 + 100);

    ULL current_hash = 0;
    ULL powerK = 1;
    for (int i = 0; i < K; ++i) powerK *= BASE;

    // Rolling hash for S2
    current_hash = 0;
    if (M >= K) {
        for (int i = 0; i < K; ++i) current_hash = current_hash * BASE + S2[i];
        
        if (0 % STEP_S2 == 0) {
            int h = current_hash & HASH_MASK;
            nodes.push_back({0, head[h]});
            head[h] = nodes.size() - 1;
        }
        for (int i = 1; i <= M - K; ++i) {
            current_hash = current_hash * BASE + S2[i + K - 1] - S2[i - 1] * powerK;
            if (i % STEP_S2 == 0) {
                int h = current_hash & HASH_MASK;
                nodes.push_back({i, head[h]});
                head[h] = nodes.size() - 1;
            }
        }
    }

    // 2. Scan S1 and find Anchors
    vector<Segment> candidates;
    candidates.reserve(100000); 

    current_hash = 0;
    if (N >= K) {
        for (int i = 0; i < K; ++i) current_hash = current_hash * BASE + S1[i];
        
        int i = 0;
        while (i <= N - K) {
            int h = current_hash & HASH_MASK;
            int best_len = -1;
            int best_j = -1;
            
            for (int p = head[h]; p != -1; p = nodes[p].next) {
                int j = nodes[p].pos;
                bool match = true;
                if (S1[i] != S2[j] || S1[i+K-1] != S2[j+K-1] || S1[i+K/2] != S2[j+K/2]) match = false;
                
                if (match) {
                    int len = K;
                    while (i + len < N && j + len < M && S1[i+len] == S2[j+len]) {
                        len++;
                    }
                    if (len > best_len) {
                        best_len = len;
                        best_j = j;
                    }
                }
            }

            if (best_len != -1) {
                candidates.push_back({i, best_j, best_len, (int)candidates.size()});
                int next_i = i + best_len; 
                if (next_i > N - K) break;
                // Recompute hash
                current_hash = 0;
                for (int k = 0; k < K; ++k) current_hash = current_hash * BASE + S1[next_i + k];
                i = next_i;
            } else {
                if (i + 1 > N - K) break;
                current_hash = current_hash * BASE + S1[i + K] - S1[i] * powerK;
                i++;
            }
        }
    }

    // 3. Chain Anchors (LIS using BIT)
    bit_init(M + 1);
    vector<int> parent(candidates.size(), -1);
    
    int max_score_global = 0;
    int best_last_idx = -1;

    for (int k = 0; k < candidates.size(); ++k) {
        int j_start = candidates[k].j;
        int len = candidates[k].len;
        int j_end = j_start + len;

        // Query best chain ending before j_start
        pair<int, int> res = bit_query(j_start + 1); 
        
        int current_score = res.first + len;
        parent[k] = res.second;

        if (current_score > max_score_global) {
            max_score_global = current_score;
            best_last_idx = k;
        }

        bit_update(j_end + 1, {current_score, k});
    }

    vector<Segment> chain;
    int cur = best_last_idx;
    while (cur != -1) {
        chain.push_back(candidates[cur]);
        cur = parent[cur];
    }
    reverse(chain.begin(), chain.end());

    // 4. Fill Gaps and generate Transcript
    string transcriptStr = "";
    int cur_i = 0;
    int cur_j = 0;

    for (const auto& seg : chain) {
        int len1 = seg.i - cur_i;
        int len2 = seg.j - cur_j;
        
        if (len1 > 0 || len2 > 0) {
            long long size_product = (long long)len1 * len2;
            if (size_product <= DP_LIMIT) {
                transcriptStr += solve_dp(S1.substr(cur_i, len1), S2.substr(cur_j, len2));
            } else {
                transcriptStr += simple_heuristic(S1.substr(cur_i, len1), S2.substr(cur_j, len2));
            }
        }
        
        for (int k = 0; k < seg.len; ++k) transcriptStr += 'M';
        
        cur_i = seg.i + seg.len;
        cur_j = seg.j + seg.len;
    }

    int len1 = N - cur_i;
    int len2 = M - cur_j;
    if (len1 > 0 || len2 > 0) {
       long long size_product = (long long)len1 * len2;
        if (size_product <= DP_LIMIT) {
            transcriptStr += solve_dp(S1.substr(cur_i, len1), S2.substr(cur_j, len2));
        } else {
            transcriptStr += simple_heuristic(S1.substr(cur_i, len1), S2.substr(cur_j, len2));
        }
    }

    cout << transcriptStr << endl;

    return 0;
}