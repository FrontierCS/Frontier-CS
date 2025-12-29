#include <bits/stdc++.h>
using namespace std;

const int N = 15;
const int P = N * N;
const int INF = 1e9;

vector<string> grid;
vector<vector<int>> pos(26);
int start_idx;

int dist(int idx1, int idx2) {
    int i1 = idx1 / N, j1 = idx1 % N;
    int i2 = idx2 / N, j2 = idx2 % N;
    return abs(i1 - i2) + abs(j1 - j2);
}

int min_cost_to_type(const string &s, int from_idx) {
    if (s.empty()) return 0;
    vector<int> dp_prev(P, INF);
    char c0 = s[0];
    for (int idx : pos[c0 - 'A']) {
        dp_prev[idx] = dist(from_idx, idx) + 1;
    }
    for (size_t i = 1; i < s.size(); ++i) {
        vector<int> dp_cur(P, INF);
        char c_cur = s[i];
        char c_prev = s[i - 1];
        for (int idx_cur : pos[c_cur - 'A']) {
            int best = INF;
            for (int idx_prev : pos[c_prev - 'A']) {
                int cost = dp_prev[idx_prev] + dist(idx_prev, idx_cur) + 1;
                if (cost < best) best = cost;
            }
            dp_cur[idx_cur] = best;
        }
        swap(dp_prev, dp_cur);
    }
    int last_c = s.back() - 'A';
    int ans = INF;
    for (int idx : pos[last_c]) {
        ans = min(ans, dp_prev[idx]);
    }
    return ans;
}

void compute_full_dp(const string &S, vector<int> &path) {
    int L = S.size();
    vector<vector<int>> dp(L, vector<int>(P, INF));
    vector<vector<int>> prev(L, vector<int>(P, -1));

    // first character
    char c0 = S[0];
    for (int idx : pos[c0 - 'A']) {
        dp[0][idx] = dist(start_idx, idx) + 1;
    }

    for (int i = 1; i < L; ++i) {
        char c_cur = S[i];
        char c_prev = S[i - 1];
        for (int idx_cur : pos[c_cur - 'A']) {
            int best = INF;
            int best_prev = -1;
            for (int idx_prev : pos[c_prev - 'A']) {
                int cost = dp[i - 1][idx_prev] + dist(idx_prev, idx_cur) + 1;
                if (cost < best) {
                    best = cost;
                    best_prev = idx_prev;
                }
            }
            dp[i][idx_cur] = best;
            prev[i][idx_cur] = best_prev;
        }
    }

    // find best ending cell
    int best_end = -1;
    int min_cost = INF;
    char last_c = S.back();
    for (int idx : pos[last_c - 'A']) {
        if (dp[L - 1][idx] < min_cost) {
            min_cost = dp[L - 1][idx];
            best_end = idx;
        }
    }

    // reconstruct path
    path.resize(L);
    int cur = best_end;
    for (int i = L - 1; i >= 0; --i) {
        path[i] = cur;
        cur = prev[i][cur];
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int M;
    cin >> N >> M;
    int si, sj;
    cin >> si >> sj;
    start_idx = si * N + sj;

    grid.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> grid[i];
    }

    vector<string> ts(M);
    for (int i = 0; i < M; ++i) {
        cin >> ts[i];
    }

    // precompute positions of each letter
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            char c = grid[i][j];
            pos[c - 'A'].push_back(i * N + j);
        }
    }

    vector<bool> covered(M, false);
    string S = "";
    vector<int> path;

    // choose initial string with minimal cost from start
    int best_init_cost = INF;
    int best_init_k = -1;
    for (int k = 0; k < M; ++k) {
        int cost = min_cost_to_type(ts[k], start_idx);
        if (cost < best_init_cost) {
            best_init_cost = cost;
            best_init_k = k;
        }
    }
    S = ts[best_init_k];
    covered[best_init_k] = true;
    compute_full_dp(S, path);
    int last_cell_idx = path.back();

    while (true) {
        // mark any already covered substrings
        bool found_any = false;
        for (int k = 0; k < M; ++k) {
            if (!covered[k] && S.find(ts[k]) != string::npos) {
                covered[k] = true;
                found_any = true;
            }
        }
        if (found_any) continue;

        // check if all covered
        bool all_covered = true;
        for (bool b : covered) {
            if (!b) {
                all_covered = false;
                break;
            }
        }
        if (all_covered) break;

        // choose the next string to append
        int best_k = -1;
        int best_add_cost = INF;
        string best_suffix;

        for (int k = 0; k < M; ++k) {
            if (covered[k]) continue;
            const string &tk = ts[k];
            // already checked that tk is not a substring of S
            // compute longest overlap between suffix of S and prefix of tk
            int max_o = 0;
            int max_len = min(S.size(), tk.size());
            for (int o = 1; o <= max_len; ++o) {
                if (S.substr(S.size() - o) == tk.substr(0, o)) {
                    max_o = o;
                }
            }
            string to_add = tk.substr(max_o);
            int add_cost = min_cost_to_type(to_add, last_cell_idx);
            if (add_cost < best_add_cost) {
                best_add_cost = add_cost;
                best_k = k;
                best_suffix = to_add;
            }
        }

        // append the chosen string
        S += best_suffix;
        covered[best_k] = true;
        compute_full_dp(S, path);
        last_cell_idx = path.back();
    }

    // output the sequence of cells
    for (int idx : path) {
        int i = idx / N;
        int j = idx % N;
        cout << i << ' ' << j << '\n';
    }

    return 0;
}