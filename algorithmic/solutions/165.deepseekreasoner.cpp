#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cstring>
#include <climits>

using namespace std;

const int N = 15;
const int INF = 1e9;

int dist(int id1, int id2) {
    int i1 = id1 / N, j1 = id1 % N;
    int i2 = id2 / N, j2 = id2 % N;
    return abs(i1 - i2) + abs(j1 - j2);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; i++) {
        cin >> grid[i];
    }
    vector<string> t(M);
    for (int i = 0; i < M; i++) {
        cin >> t[i];
    }

    // letter -> list of cell ids
    vector<vector<int>> letter_cells(26);
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int id = i * N + j;
            letter_cells[grid[i][j] - 'A'].push_back(id);
        }
    }

    int total_cells = N * N;

    // Precompute h[t_idx][p][start_id] -> {movement, end_cell_id}
    // p = 0..4, suffix length = 5-p
    vector<vector<vector<pair<int, int>>>> h(M, vector<vector<pair<int, int>>>(5, vector<pair<int, int>>(total_cells, {INF, -1})));

    for (int tidx = 0; tidx < M; tidx++) {
        const string& str = t[tidx];
        for (int p = 0; p < 5; p++) {
            int L = 5 - p;
            for (int start_id = 0; start_id < total_cells; start_id++) {
                // DP layers
                vector<vector<int>> dp(L, vector<int>(total_cells, INF));
                // step 0
                char c0 = str[p];
                for (int cell : letter_cells[c0 - 'A']) {
                    dp[0][cell] = dist(start_id, cell);
                }
                // steps 1..L-1
                for (int k = 1; k < L; k++) {
                    char c_prev = str[p + k - 1];
                    char c_cur = str[p + k];
                    for (int cur_cell : letter_cells[c_cur - 'A']) {
                        int best = INF;
                        for (int prev_cell : letter_cells[c_prev - 'A']) {
                            int val = dp[k-1][prev_cell] + dist(prev_cell, cur_cell);
                            if (val < best) best = val;
                        }
                        dp[k][cur_cell] = best;
                    }
                }
                // find min in last layer
                int min_mov = INF;
                int end_cell = -1;
                char last_c = str[p + L - 1];
                for (int cell : letter_cells[last_c - 'A']) {
                    if (dp[L-1][cell] < min_mov) {
                        min_mov = dp[L-1][cell];
                        end_cell = cell;
                    }
                }
                h[tidx][p][start_id] = {min_mov, end_cell};
            }
        }
    }

    // Greedy construction
    int cur_id = si * N + sj;
    string S_full = "";
    vector<bool> covered(M, false);
    vector<pair<int, int>> output; // list of (i,j)

    while (true) {
        // Check if any uncovered string is already a substring of S_full
        bool changed = false;
        for (int i = 0; i < M; i++) {
            if (!covered[i] && S_full.find(t[i]) != string::npos) {
                covered[i] = true;
                changed = true;
            }
        }
        if (count(covered.begin(), covered.end(), true) == M) break;

        // Find best string to add
        int best_t = -1, best_o = -1;
        int best_cost = INF;
        int best_end = -1;
        for (int i = 0; i < M; i++) {
            if (covered[i]) continue;
            const string& str = t[i];
            int max_o = min(4, (int)S_full.size());
            for (int o = 0; o <= max_o; o++) {
                if (S_full.substr(S_full.size() - o) == str.substr(0, o)) {
                    pair<int, int> res = h[i][o][cur_id];
                    int add_cost = res.first + (5 - o);
                    if (add_cost < best_cost) {
                        best_cost = add_cost;
                        best_t = i;
                        best_o = o;
                        best_end = res.second;
                    }
                }
            }
        }
        // Fallback: no overlap found (should not happen, but just in case)
        if (best_t == -1) {
            best_o = 0;
            best_cost = INF;
            for (int i = 0; i < M; i++) {
                if (covered[i]) continue;
                pair<int, int> res = h[i][0][cur_id];
                int add_cost = res.first + 5;
                if (add_cost < best_cost) {
                    best_cost = add_cost;
                    best_t = i;
                    best_end = res.second;
                }
            }
        }

        // Add the string best_t with overlap best_o
        const string& str = t[best_t];
        int L = 5 - best_o;
        vector<int> dp_prev(total_cells, INF);
        vector<int> dp_cur(total_cells, INF);
        vector<vector<int>> prev(L, vector<int>(total_cells, -1)); // for k>=1

        // Step 0
        char c0 = str[best_o];
        for (int cell : letter_cells[c0 - 'A']) {
            dp_cur[cell] = dist(cur_id, cell);
        }

        // Steps 1..L-1
        for (int k = 1; k < L; k++) {
            swap(dp_prev, dp_cur);
            fill(dp_cur.begin(), dp_cur.end(), INF);
            char c_prev = str[best_o + k - 1];
            char c_cur = str[best_o + k];
            for (int cell : letter_cells[c_cur - 'A']) {
                int best = INF;
                int best_prev = -1;
                for (int prev_cell : letter_cells[c_prev - 'A']) {
                    int val = dp_prev[prev_cell] + dist(prev_cell, cell);
                    if (val < best) {
                        best = val;
                        best_prev = prev_cell;
                    }
                }
                dp_cur[cell] = best;
                prev[k][cell] = best_prev;
            }
        }

        // Find end cell
        int min_mov = INF;
        int end_cell = -1;
        char last_c = str[best_o + L - 1];
        for (int cell : letter_cells[last_c - 'A']) {
            if (dp_cur[cell] < min_mov) {
                min_mov = dp_cur[cell];
                end_cell = cell;
            }
        }

        // Backtrack to get cell sequence
        vector<int> cell_seq(L);
        cell_seq[L-1] = end_cell;
        for (int k = L-1; k > 0; k--) {
            cell_seq[k-1] = prev[k][cell_seq[k]];
        }

        // Append to output
        for (int id : cell_seq) {
            output.push_back({id / N, id % N});
        }

        // Update state
        S_full += str.substr(best_o);
        cur_id = end_cell;
        covered[best_t] = true;
    }

    // Output
    for (auto& p : output) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}