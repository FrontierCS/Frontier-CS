#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <queue>
#include <map>
#include <numeric>
#include <tuple>

using namespace std;

long long query(int l, int t) {
    cout << "? " << l << " " << t << endl;
    long long response;
    cin >> response;
    return response;
}

void solve() {
    int n;
    int m;
    cin >> n >> m;

    // Grid is not used by the solution, but needs to be read.
    vector<vector<int>> g(n, vector<int>(n));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> g[i][j];
        }
    }

    int max_t = 2 * n - 1;

    vector<pair<long long, int>> max_vals(max_t);
    for (int t = 1; t <= max_t; ++t) {
        max_vals[t - 1] = {query(n, t), t};
    }

    sort(max_vals.begin(), max_vals.end());

    vector<int> sorted_t(max_t);
    for (int i = 0; i < max_t; ++i) {
        sorted_t[i] = max_vals[i].second;
    }

    priority_queue<tuple<long long, int, int>, vector<tuple<long long, int, int>>, greater<tuple<long long, int, int>>> pq;
    vector<vector<bool>> visited(n + 1, vector<bool>(max_t + 1, false));

    vector<long long> answers;
    int next_t_idx = 0;

    while (answers.size() < m) {
        while (next_t_idx < max_t) {
            bool should_add_column = false;
            if (pq.empty()) {
                should_add_column = true;
            } else {
                long long current_min_val = get<0>(pq.top());
                if (current_min_val > max_vals[next_t_idx].first) {
                    should_add_column = true;
                }
            }

            if (should_add_column) {
                int t_to_add = sorted_t[next_t_idx];
                if (!visited[1][t_to_add]) {
                    long long val = query(1, t_to_add);
                    pq.push({val, 1, t_to_add});
                    visited[1][t_to_add] = true;
                }
                next_t_idx++;
            } else {
                break;
            }
        }
        
        if (pq.empty()) {
            break;
        }

        auto [val, l, t] = pq.top();
        pq.pop();

        answers.push_back(val);
        if (answers.size() == m) {
            break;
        }

        if (l < n) {
            if (!visited[l + 1][t]) {
                long long next_val = query(l + 1, t);
                pq.push({next_val, l + 1, t});
                visited[l + 1][t] = true;
            }
        }
    }

    cout << "!";
    for (int i = 0; i < m; ++i) {
        cout << " " << answers[i];
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