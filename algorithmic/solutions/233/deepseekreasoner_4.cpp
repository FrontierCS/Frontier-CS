#include <bits/stdc++.h>
using namespace std;

const int INF = 1e9;

struct Query {
    int lb, l, T;
    Query(int lb, int l, int T) : lb(lb), l(l), T(T) {}
    bool operator<(const Query& other) const {
        if (lb != other.lb) return lb < other.lb;
        return l > other.l; // tie-break: larger l first (cheaper)
    }
};

void solve() {
    int n, m;
    cin >> n >> m;
    vector<vector<int>> G(n+1, vector<int>(n+1));
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cin >> G[i][j];
        }
    }

    // precompute min value on each diagonal i+j = s
    vector<int> min_diag(2*n+2, INF);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            int s = i + j;
            min_diag[s] = min(min_diag[s], G[i][j]);
        }
    }

    // precompute prefix max of row 1
    vector<int> row1_max(n+1);
    row1_max[0] = 0;
    for (int j = 1; j <= n; ++j) {
        row1_max[j] = max(row1_max[j-1], G[1][j]);
    }

    // precompute for each l the max of min_diag[s] for s=2..l+1
    vector<int> min_diag_max(n+1);
    int cur_max = 0;
    for (int l = 1; l <= n; ++l) {
        // diagonal l+1 is new
        cur_max = max(cur_max, min_diag[l+1]);
        min_diag_max[l] = cur_max;
    }

    vector<Query> queries;
    for (int l = 1; l <= n; ++l) {
        for (int T = 1; T <= 2*n-1; ++T) {
            int lb;
            if (T >= l) {
                int s_start = T - l + 2;
                int s_end = T + 1;
                int mx = 0;
                for (int s = s_start; s <= s_end; ++s) {
                    mx = max(mx, min_diag[s]);
                }
                lb = mx;
            } else {
                // T < l
                int mx1 = min_diag_max[l];
                int start_col = l - T + 1;
                int end_col = l;
                int mx2 = 0;
                for (int c = start_col; c <= end_col; ++c) {
                    mx2 = max(mx2, G[1][c]);
                }
                lb = max(mx1, mx2);
            }
            queries.emplace_back(lb, l, T);
        }
    }

    sort(queries.begin(), queries.end());

    priority_queue<int> pq; // max-heap of smallest m values seen
    int K = INF; // current m-th smallest (if pq.size() == m)
    int queries_made = 0;
    for (const Query& q : queries) {
        if (pq.size() == m && q.lb >= K) {
            break;
        }
        cout << "? " << q.l << " " << q.T << endl;
        cout.flush();
        int val;
        cin >> val;
        queries_made++;
        if (pq.size() < m) {
            pq.push(val);
            if (pq.size() == m) {
                K = pq.top();
            }
        } else {
            if (val < pq.top()) {
                pq.pop();
                pq.push(val);
                K = pq.top();
            }
        }
    }

    // Extract values from heap and sort
    vector<int> ans;
    while (!pq.empty()) {
        ans.push_back(pq.top());
        pq.pop();
    }
    sort(ans.begin(), ans.end());
    cout << "!";
    for (int x : ans) {
        cout << " " << x;
    }
    cout << endl;
    cout.flush();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}