#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <tuple>

using namespace std;

const int INF = 1e9 + 7;

int ask(int l, int t) {
    cout << "? " << l << " " << t << endl;
    int response;
    cin >> response;
    return response;
}

void solve() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> g(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> g[i][j];
        }
    }

    vector<vector<vector<int>>> dp(2, vector<vector<int>>(2 * n - 1, vector<int>(n + 1, INF)));

    int prev_l_idx = 0;
    int curr_l_idx = 1;

    vector<tuple<int, int, int>> candidates;

    // len = 1
    for (int t = 0; t < 2 * n - 1; ++t) {
        int min_val_for_t = INF;
        for (int r = 1; r <= n; ++r) {
            int c = t + 2 - r;
            if (c >= 1 && c <= n) {
                dp[prev_l_idx][t][r] = g[r - 1][c - 1];
                min_val_for_t = min(min_val_for_t, dp[prev_l_idx][t][r]);
            }
        }
        if (min_val_for_t != INF) {
            candidates.emplace_back(min_val_for_t, -1, t + 1);
        }
    }

    for (int len = 2; len <= n; ++len) {
        for (int t = len - 1; t < 2 * n - 1; ++t) {
            int min_val_for_t = INF;
            for (int r = 1; r <= n; ++r) {
                int c = t + 2 - r;
                if (c < 1 || c > n) {
                    dp[curr_l_idx][t][r] = INF;
                    continue;
                }

                int prev_min_val = INF;
                if (r > 1) {
                    prev_min_val = min(prev_min_val, dp[prev_l_idx][t - 1][r - 1]);
                }
                if (c > 1) {
                    prev_min_val = min(prev_min_val, dp[prev_l_idx][t - 1][r]);
                }

                if (prev_min_val != INF) {
                    dp[curr_l_idx][t][r] = max(g[r - 1][c - 1], prev_min_val);
                    min_val_for_t = min(min_val_for_t, dp[curr_l_idx][t][r]);
                } else {
                    dp[curr_l_idx][t][r] = INF;
                }
            }
            if (min_val_for_t != INF) {
                candidates.emplace_back(min_val_for_t, -len, t + 1);
            }
        }
        swap(prev_l_idx, curr_l_idx);
    }

    sort(candidates.begin(), candidates.end());

    multiset<int> results;
    for (const auto& cand : candidates) {
        int v_min = get<0>(cand);
        int l = -get<1>(cand);
        int t = get<2>(cand);

        if (results.size() < m) {
            results.insert(ask(l, t));
        } else {
            int max_in_results = *results.rbegin();
            if (v_min >= max_in_results) {
                break;
            }
            int true_val = ask(l, t);
            if (true_val < max_in_results) {
                results.erase(prev(results.end()));
                results.insert(true_val);
            }
        }
    }

    cout << "!";
    for (int val : results) {
        cout << " " << val;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}