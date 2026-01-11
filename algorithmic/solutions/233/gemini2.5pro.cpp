#include <iostream>
#include <vector>
#include <algorithm>
#include <deque>
#include <queue>
#include <tuple>

using namespace std;

int query(int l, int T) {
    cout << "? " << l << " " << T << endl;
    int response;
    cin >> response;
    return response;
}

void solve() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> G(n + 1, vector<int>(n + 1));
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cin >> G[i][j];
        }
    }

    vector<int> min_val(2 * n, 1e9 + 7);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (i + j - 1 < 2 * n) {
                min_val[i + j - 1] = min(min_val[i + j - 1], G[i][j]);
            }
        }
    }

    vector<tuple<int, int, int>> candidates;
    candidates.reserve(n * (2 * n - 1));
    for (int l = 1; l <= n; ++l) {
        deque<pair<int, int>> dq;
        for (int T = 1; T < 2 * n; ++T) {
            int window_start_k = max(1, T - l + 1);
            
            while (!dq.empty() && dq.back().first >= min_val[T]) {
                dq.pop_back();
            }
            dq.push_back({min_val[T], T});

            while (!dq.empty() && dq.front().second < window_start_k) {
                dq.pop_front();
            }
            
            int lb = dq.front().first;
            candidates.emplace_back(lb, -l, T);
        }
    }

    sort(candidates.begin(), candidates.end());

    priority_queue<int> pq;
    for (const auto& cand : candidates) {
        int lb, neg_l, T;
        tie(lb, neg_l, T) = cand;
        int l = -neg_l;

        if (pq.size() == m && lb >= pq.top()) {
            break;
        }

        int val = query(l, T);

        if (pq.size() < m) {
            pq.push(val);
        } else if (val < pq.top()) {
            pq.pop();
            pq.push(val);
        }
    }

    vector<int> result;
    result.reserve(m);
    while (!pq.empty()) {
        result.push_back(pq.top());
        pq.pop();
    }
    sort(result.begin(), result.end());

    cout << "! ";
    for (int i = 0; i < m; ++i) {
        cout << result[i] << (i == m - 1 ? "" : " ");
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