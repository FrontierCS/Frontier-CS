#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <climits>
#include <cassert>

using namespace std;

const int N = 15;
const int INF = 1e9;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(n);
    for (int i = 0; i < n; ++i) {
        cin >> grid[i];
    }
    vector<string> patterns(m);
    for (int i = 0; i < m; ++i) {
        cin >> patterns[i];
    }

    // ---------- Step 1: Build superstring by greedy merging ----------
    vector<string> cur = patterns;
    // Precompute overlap matrix for current list? But list changes.
    // We'll compute on the fly each iteration.
    while (cur.size() > 1) {
        int best_overlap = -1;
        int best_i = -1, best_j = -1;
        bool best_dir = false; // false: i then j, true: j then i

        for (size_t i = 0; i < cur.size(); ++i) {
            for (size_t j = 0; j < cur.size(); ++j) {
                if (i == j) continue;
                // Overlap suffix of i with prefix of j
                int len_i = cur[i].size();
                int len_j = cur[j].size();
                int max_possible = min(len_i, len_j);
                int overlap = 0;
                for (int l = 1; l <= max_possible; ++l) {
                    if (cur[i].substr(len_i - l) == cur[j].substr(0, l)) {
                        overlap = l;
                    }
                }
                if (overlap > best_overlap) {
                    best_overlap = overlap;
                    best_i = i;
                    best_j = j;
                    best_dir = false;
                }
                // Overlap suffix of j with prefix of i
                overlap = 0;
                for (int l = 1; l <= max_possible; ++l) {
                    if (cur[j].substr(len_j - l) == cur[i].substr(0, l)) {
                        overlap = l;
                    }
                }
                if (overlap > best_overlap) {
                    best_overlap = overlap;
                    best_i = i;
                    best_j = j;
                    best_dir = true;
                }
            }
        }

        // Merge best_i and best_j
        string new_str;
        if (!best_dir) {
            // cur[best_i] then cur[best_j] with overlap
            new_str = cur[best_i] + cur[best_j].substr(best_overlap);
        } else {
            // cur[best_j] then cur[best_i] with overlap
            new_str = cur[best_j] + cur[best_i].substr(best_overlap);
        }
        // Remove two strings and add new one
        int idx1 = max(best_i, best_j);
        int idx2 = min(best_i, best_j);
        cur.erase(cur.begin() + idx1);
        cur.erase(cur.begin() + idx2);
        cur.push_back(new_str);
    }

    string S = cur[0];
    int L = S.size();
    // Ensure L <= 5000 (it will be at most ~1000)
    if (L > 5000) {
        // Fallback: just concatenate patterns (should not happen)
        S.clear();
        for (const string& p : patterns) S += p;
        L = S.size();
    }

    // ---------- Step 2: DP for optimal path to type S ----------
    // Precompute positions for each letter
    vector<vector<pair<int,int>>> pos_by_letter(26);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c = grid[i][j] - 'A';
            pos_by_letter[c].emplace_back(i, j);
        }
    }

    // dp_prev and dp_cur are 2D arrays
    vector<vector<int>> dp_prev(n, vector<int>(n, INF));
    // For first character
    char first_char = S[0];
    for (auto [x, y] : pos_by_letter[first_char - 'A']) {
        int cost = abs(x - si) + abs(y - sj) + 1;
        dp_prev[x][y] = cost;
    }

    // prev_step[l][x][y] stores the previous cell (at step l-1) that leads to (x,y) at step l.
    // We only need to store for l = 1..L-1.
    // We'll use a 3D vector: prev_step[l][x][y] = (px, py)
    vector<vector<vector<pair<int,int>>>> prev_step(L, vector<vector<pair<int,int>>>(n, vector<pair<int,int>>(n, {-1,-1})));

    // For each subsequent character
    for (int idx = 1; idx < L; ++idx) {
        char need = S[idx];
        // Initialize cur_val and cur_src from dp_prev
        vector<vector<int>> cur_val = dp_prev;
        vector<vector<pair<int,int>>> cur_src(n, vector<pair<int,int>>(n, {-1,-1}));
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                if (dp_prev[i][j] < INF) {
                    cur_src[i][j] = {i, j};
                }
            }
        }

        // L1 distance transform: row passes
        for (int i = 0; i < n; ++i) {
            // left to right
            for (int j = 1; j < n; ++j) {
                int cand = cur_val[i][j-1] + 1;
                if (cand < cur_val[i][j]) {
                    cur_val[i][j] = cand;
                    cur_src[i][j] = cur_src[i][j-1];
                }
            }
            // right to left
            for (int j = n-2; j >= 0; --j) {
                int cand = cur_val[i][j+1] + 1;
                if (cand < cur_val[i][j]) {
                    cur_val[i][j] = cand;
                    cur_src[i][j] = cur_src[i][j+1];
                }
            }
        }
        // column passes
        for (int j = 0; j < n; ++j) {
            // top to bottom
            for (int i = 1; i < n; ++i) {
                int cand = cur_val[i-1][j] + 1;
                if (cand < cur_val[i][j]) {
                    cur_val[i][j] = cand;
                    cur_src[i][j] = cur_src[i-1][j];
                }
            }
            // bottom to top
            for (int i = n-2; i >= 0; --i) {
                int cand = cur_val[i+1][j] + 1;
                if (cand < cur_val[i][j]) {
                    cur_val[i][j] = cand;
                    cur_src[i][j] = cur_src[i+1][j];
                }
            }
        }

        // Now compute dp_cur for cells with the needed letter
        vector<vector<int>> dp_cur(n, vector<int>(n, INF));
        for (auto [x, y] : pos_by_letter[need - 'A']) {
            dp_cur[x][y] = cur_val[x][y] + 1;
            prev_step[idx][x][y] = cur_src[x][y];
        }
        dp_prev = move(dp_cur);
    }

    // Find the best ending cell
    int best_x = -1, best_y = -1;
    int best_cost = INF;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (dp_prev[i][j] < best_cost) {
                best_cost = dp_prev[i][j];
                best_x = i;
                best_y = j;
            }
        }
    }

    // Backtrack to get the full path
    vector<pair<int,int>> path(L);
    path[L-1] = {best_x, best_y};
    for (int idx = L-1; idx > 0; --idx) {
        auto [px, py] = prev_step[idx][path[idx].first][path[idx].second];
        path[idx-1] = {px, py};
    }

    // Output
    for (auto [x, y] : path) {
        cout << x << " " << y << "\n";
    }

    return 0;
}