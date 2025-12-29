#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <climits>
#include <cstdlib>
#include <ctime>

using namespace std;

const int N = 15;
const int INF = 1e9;

vector<vector<short>> dist; // distance matrix 225x225
vector<vector<int>> pos(26); // positions for each letter

// convert (i,j) to index
int to_idx(int i, int j) {
    return i * N + j;
}

// precompute Manhattan distances
void precompute_dist() {
    int total = N * N;
    dist.resize(total, vector<short>(total));
    for (int a = 0; a < total; ++a) {
        int i1 = a / N, j1 = a % N;
        for (int b = 0; b < total; ++b) {
            int i2 = b / N, j2 = b % N;
            dist[a][b] = abs(i1 - i2) + abs(j1 - j2);
        }
    }
}

// compute longest suffix of a that equals prefix of b
int overlap(const string& a, const string& b) {
    int max_len = min(a.size(), b.size());
    for (int l = max_len; l >= 0; --l) {
        if (a.substr(a.size() - l) == b.substr(0, l))
            return l;
    }
    return 0;
}

// pairwise greedy superstring
string pairwise_greedy(const vector<string>& t) {
    vector<string> cur = t;
    while (cur.size() > 1) {
        int max_ov = -1;
        int a_idx = -1, b_idx = -1;
        bool a_before_b = true;
        for (size_t i = 0; i < cur.size(); ++i) {
            for (size_t j = 0; j < cur.size(); ++j) {
                if (i == j) continue;
                int ov = overlap(cur[i], cur[j]);
                if (ov > max_ov) {
                    max_ov = ov;
                    a_idx = i;
                    b_idx = j;
                    a_before_b = true;
                }
                int ov2 = overlap(cur[j], cur[i]);
                if (ov2 > max_ov) {
                    max_ov = ov2;
                    a_idx = j;
                    b_idx = i;
                    a_before_b = false;
                }
            }
        }
        if (max_ov < 0) max_ov = 0; // just concatenate
        string merged;
        if (a_before_b) {
            merged = cur[a_idx] + cur[b_idx].substr(max_ov);
        } else {
            merged = cur[a_idx] + cur[b_idx].substr(max_ov);
        }
        // remove the two strings (higher index first)
        int i1 = max(a_idx, b_idx);
        int i2 = min(a_idx, b_idx);
        cur.erase(cur.begin() + i1);
        cur.erase(cur.begin() + i2);
        cur.push_back(merged);
    }
    return cur[0];
}

// sequential greedy superstring starting from given index
string sequential_greedy(const vector<string>& t, int start_idx) {
    int M = t.size();
    vector<bool> used(M, false);
    string current = t[start_idx];
    used[start_idx] = true;
    int remaining = M - 1;
    while (remaining > 0) {
        // first, mark any unused string that is already a substring of current
        for (int i = 0; i < M; ++i) {
            if (!used[i] && current.find(t[i]) != string::npos) {
                used[i] = true;
                --remaining;
            }
        }
        if (remaining == 0) break;
        int best_ov = -1;
        int best_idx = -1;
        bool prepend = false;
        for (int i = 0; i < M; ++i) {
            if (used[i]) continue;
            // try to append at the end
            int ov = overlap(current, t[i]);
            if (ov > best_ov) {
                best_ov = ov;
                best_idx = i;
                prepend = false;
            }
            // try to prepend at the beginning
            ov = overlap(t[i], current);
            if (ov > best_ov) {
                best_ov = ov;
                best_idx = i;
                prepend = true;
            }
        }
        if (best_idx == -1) break; // should not happen
        if (!prepend) {
            current = current + t[best_idx].substr(best_ov);
        } else {
            current = t[best_idx] + current.substr(best_ov);
        }
        used[best_idx] = true;
        --remaining;
    }
    return current;
}

// DP to find optimal cell sequence for a given string S, starting from start_cell
// returns (total_cost, sequence of cell indices)
pair<int, vector<int>> find_path(const string& S, int start_cell) {
    int L = S.size();
    // step_cells[s] : list of cells for step s (s from 0 to L)
    // step 0: only start_cell
    vector<vector<int>> step_cells(L + 1);
    vector<vector<int>> step_cost(L + 1);
    vector<vector<int>> step_prev(L + 1); // for step s, index in step_cells[s-1]
    step_cells[0] = {start_cell};
    step_cost[0] = {0};
    step_prev[0] = {};
    for (int s = 1; s <= L; ++s) {
        char c = S[s - 1];
        vector<int>& cells = pos[c - 'A'];
        int m = cells.size();
        step_cells[s].resize(m);
        step_cost[s].assign(m, INF);
        step_prev[s].assign(m, -1);
        for (int i = 0; i < m; ++i) {
            int cell = cells[i];
            step_cells[s][i] = cell;
            // iterate over previous step's cells
            for (int j = 0; j < step_cells[s-1].size(); ++j) {
                int prev_cell = step_cells[s-1][j];
                int cost = step_cost[s-1][j] + dist[prev_cell][cell] + 1;
                if (cost < step_cost[s][i]) {
                    step_cost[s][i] = cost;
                    step_prev[s][i] = j;
                }
            }
        }
    }
    // find best at final step
    int best_idx = 0;
    for (int i = 1; i < step_cells[L].size(); ++i) {
        if (step_cost[L][i] < step_cost[L][best_idx])
            best_idx = i;
    }
    int total_cost = step_cost[L][best_idx];
    // reconstruct path
    vector<int> cell_seq(L);
    int idx = best_idx;
    for (int s = L; s >= 1; --s) {
        cell_seq[s-1] = step_cells[s][idx];
        idx = step_prev[s][idx];
    }
    return {total_cost, cell_seq};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;
    int start_cell = to_idx(si, sj);
    // read grid
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) {
        cin >> grid[i];
    }
    // precompute letter positions
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c = grid[i][j];
            pos[c - 'A'].push_back(to_idx(i, j));
        }
    }
    // read target strings
    vector<string> t(M);
    for (int i = 0; i < M; ++i) {
        cin >> t[i];
    }
    // precompute distances
    precompute_dist();
    // generate candidate superstrings
    vector<string> candidates;
    // 1. pairwise greedy
    candidates.push_back(pairwise_greedy(t));
    // 2. sequential greedy with first 10 strings as starters
    for (int start = 0; start < 10 && start < M; ++start) {
        candidates.push_back(sequential_greedy(t, start));
    }
    // find best candidate
    int best_cost = INF;
    vector<int> best_seq;
    for (const string& S : candidates) {
        auto [cost, seq] = find_path(S, start_cell);
        if (cost < best_cost) {
            best_cost = cost;
            best_seq = seq;
        }
    }
    // output the cell sequence
    for (int cell : best_seq) {
        int i = cell / N;
        int j = cell % N;
        cout << i << " " << j << "\n";
    }
    return 0;
}