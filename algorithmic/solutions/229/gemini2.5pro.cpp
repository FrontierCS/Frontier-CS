#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

const long long INF = 1e18;
const int MAX_OPS = 10;
const int K = MAX_OPS + 1;

int n;
long long x;
vector<int> t;

vector<vector<long long>> dp;
vector<vector<int>> opt;

vector<int> lis_vals;
vector<int> m_lis;

int calculate_lis(int l, int r) {
    if (l > r) {
        return 0;
    }
    vector<int> m;
    for (int i = l; i <= r; ++i) {
        auto it = lower_bound(m.begin(), m.end(), t[i]);
        if (it == m.end()) {
            m.push_back(t[i]);
        } else {
            *it = t[i];
        }
    }
    return m.size();
}

void compute(int k, int l, int r, int optl, int optr) {
    if (l > r) {
        return;
    }

    int mid = l + (r - l) / 2;
    long long best_val = -INF;
    int best_p = optl;

    m_lis.clear();
    int upper_p = min(mid - 1, optr);

    for (int p = mid - 1; p >= upper_p; --p) {
        auto it = lower_bound(m_lis.begin(), m_lis.end(), t[p]);
        if (it == m_lis.end()) {
            m_lis.push_back(t[p]);
        } else {
            *it = t[p];
        }
    }

    for (int p = upper_p; p >= optl; --p) {
        if (dp[k - 1][p] > -INF / 2) {
            long long current_val = dp[k - 1][p] + m_lis.size();
            if (current_val > best_val) {
                best_val = current_val;
                best_p = p;
            }
        }
        if (p > optl) {
            auto it = lower_bound(m_lis.begin(), m_lis.end(), t[p - 1]);
            if (it == m_lis.end()) {
                m_lis.push_back(t[p - 1]);
            } else {
                *it = t[p - 1];
            }
        }
    }

    dp[k][mid] = best_val;
    opt[k][mid] = best_p;

    if (l <= mid - 1) {
        compute(k, l, mid - 1, optl, best_p);
    }
    if (mid + 1 <= r) {
        compute(k, mid + 1, r, best_p, optr);
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> x;
    t.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> t[i];
    }

    dp.assign(K + 1, vector<long long>(n + 1, -INF));
    opt.assign(K + 1, vector<int>(n + 1, 0));

    dp[0][0] = 0;

    for (int k = 1; k <= K; ++k) {
        compute(k, 1, n, 0, n - 1);
    }

    long long max_lis = calculate_lis(0, n - 1);
    int num_ops = 0;
    
    for (int k = 2; k <= K; ++k) {
        if (dp[k][n] > max_lis) {
            max_lis = dp[k][n];
            num_ops = k - 1;
        }
    }
    
    cout << max_lis << endl;

    vector<int> splits;
    if (num_ops > 0) {
        int current_n = n;
        int current_k = num_ops + 1;
        while (current_k > 1) {
            int p = opt[current_k][current_n];
            splits.push_back(p);
            current_n = p;
            current_k--;
        }
    }
    reverse(splits.begin(), splits.end());

    vector<pair<pair<int, int>, long long>> ops;
    if (x > 0) {
        for (int p : splits) {
            ops.push_back({{p + 1, n}, x});
        }
    }

    for (int i = 0; i < MAX_OPS; ++i) {
        if (i < ops.size()) {
            cout << ops[i].first.first << " " << ops[i].first.second << " " << ops[i].second << endl;
        } else {
            cout << 1 << " " << 1 << " " << 0 << endl;
        }
    }

    return 0;
}