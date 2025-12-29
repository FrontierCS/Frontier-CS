#include <bits/stdc++.h>
#include <random>
#include <chrono>
using namespace std;

const int INF = 1e9;
const int N = 15;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

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

    // Preprocess positions for each letter
    vector<vector<int>> pos_for_letter(26);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int letter = grid[i][j] - 'A';
            int id = i * n + j;
            pos_for_letter[letter].push_back(id);
        }
    }

    // Precompute Manhattan distances between all pairs of cells
    vector<vector<int>> dist(n * n, vector<int>(n * n));
    for (int id1 = 0; id1 < n * n; ++id1) {
        int i1 = id1 / n, j1 = id1 % n;
        for (int id2 = 0; id2 < n * n; ++id2) {
            int i2 = id2 / n, j2 = id2 % n;
            dist[id1][id2] = abs(i1 - i2) + abs(j1 - j2);
        }
    }

    // Helper: longest suffix of a that is prefix of b
    auto overlap_len = [](const string& a, const string& b) -> int {
        int max_len = min(a.size(), b.size());
        for (int len = max_len; len >= 1; --len) {
            if (a.substr(a.size() - len) == b.substr(0, len))
                return len;
        }
        return 0;
    };

    // Greedy pairwise merging to find a short superstring
    string best_S = "";
    int best_len = INF;
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    int num_trials = 10;
    for (int trial = 0; trial < num_trials; ++trial) {
        vector<string> cur_patterns = patterns;
        shuffle(cur_patterns.begin(), cur_patterns.end(), rng);
        vector<string> active = cur_patterns;

        while (active.size() > 1) {
            int max_ov = -1;
            int a_idx = -1, b_idx = -1;
            bool a_before_b = true;
            int k = active.size();
            for (int i = 0; i < k; ++i) {
                for (int j = i + 1; j < k; ++j) {
                    int ov_ij = overlap_len(active[i], active[j]);
                    int ov_ji = overlap_len(active[j], active[i]);
                    if (ov_ij > max_ov) {
                        max_ov = ov_ij;
                        a_idx = i;
                        b_idx = j;
                        a_before_b = true;
                    }
                    if (ov_ji > max_ov) {
                        max_ov = ov_ji;
                        a_idx = j;
                        b_idx = i;
                        a_before_b = false;
                    }
                }
            }
            // Merge the best pair
            string new_str;
            if (a_before_b)
                new_str = active[a_idx] + active[b_idx].substr(max_ov);
            else
                new_str = active[b_idx] + active[a_idx].substr(max_ov);
            // Replace a_idx with new_str and remove b_idx
            active[a_idx] = new_str;
            active.erase(active.begin() + b_idx);
        }

        string S = active[0];
        // Ensure all patterns appear (should already, but safety)
        for (const string& pat : patterns) {
            if (S.find(pat) == string::npos)
                S += pat;
        }
        if ((int)S.length() < best_len) {
            best_len = S.length();
            best_S = S;
        }
    }

    string S = best_S;
    int L = S.length();

    // Dynamic programming to plan the minimal cost path
    int start_id = si * n + sj;
    vector<vector<int>> dp(L, vector<int>(n * n, INF));
    vector<vector<int>> parent(L, vector<int>(n * n, -1));

    // First character
    int first_letter = S[0] - 'A';
    for (int p : pos_for_letter[first_letter]) {
        dp[0][p] = dist[start_id][p] + 1;
        parent[0][p] = start_id;
    }

    // Subsequent characters
    for (int idx = 1; idx < L; ++idx) {
        int letter = S[idx] - 'A';
        int prev_letter = S[idx - 1] - 'A';
        for (int p : pos_for_letter[letter]) {
            int best_cost = INF;
            int best_q = -1;
            for (int q : pos_for_letter[prev_letter]) {
                if (dp[idx - 1][q] < INF) {
                    int cost = dp[idx - 1][q] + dist[q][p] + 1;
                    if (cost < best_cost) {
                        best_cost = cost;
                        best_q = q;
                    }
                }
            }
            if (best_q != -1) {
                dp[idx][p] = best_cost;
                parent[idx][p] = best_q;
            }
        }
    }

    // Find best ending position
    int last_letter = S[L - 1] - 'A';
    int best_end = -1;
    int min_cost = INF;
    for (int p : pos_for_letter[last_letter]) {
        if (dp[L - 1][p] < min_cost) {
            min_cost = dp[L - 1][p];
            best_end = p;
        }
    }

    // Reconstruct the sequence of positions
    vector<int> path_ids(L);
    int cur = best_end;
    for (int idx = L - 1; idx >= 0; --idx) {
        path_ids[idx] = cur;
        cur = parent[idx][cur];
    }

    // Output
    for (int id : path_ids) {
        int i = id / n;
        int j = id % n;
        cout << i << " " << j << "\n";
    }

    return 0;
}