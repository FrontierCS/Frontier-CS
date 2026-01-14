#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

const long long INF = 4e18; 

template <class T>
struct SegTree {
    int n;
    vector<T> t;
    T neutral;

    SegTree(int size, T neutral_val) : n(size), neutral(neutral_val) {
        t.assign(4 * n, neutral);
    }

    void update(int v, int tl, int tr, int pos, T new_val) {
        if (tl == tr) {
            t[v] = new_val;
        } else {
            int tm = tl + (tr - tl) / 2;
            if (pos <= tm) {
                update(2 * v, tl, tm, pos, new_val);
            } else {
                update(2 * v + 1, tm + 1, tr, pos, new_val);
            }
            t[v] = max(t[2 * v], t[2 * v + 1]);
        }
    }

    T query(int v, int tl, int tr, int l, int r) {
        if (l > r) {
            return neutral;
        }
        if (l == tl && r == tr) {
            return t[v];
        }
        int tm = tl + (tr - tl) / 2;
        return max(query(2 * v, tl, tm, l, min(r, tm)),
                   query(2 * v + 1, tm + 1, tr, max(l, tm + 1), r));
    }

    void update(int pos, T new_val) {
        update(1, 0, n - 1, pos, new_val);
    }

    T query(int l, int r) {
        if (l > r || l < 0 || r >= n) return neutral;
        return query(1, 0, n - 1, l, r);
    }
};

void solve() {
    int n, m;
    long long c;
    cin >> n >> m >> c;

    vector<long long> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    vector<long long> b(m);
    for (int i = 0; i < m; ++i) {
        cin >> b[i];
    }

    vector<long long> pa(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pa[i + 1] = pa[i] + a[i];
    }

    vector<long long> pb(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        pb[i + 1] = pb[i] + b[i];
    }

    vector<long long> dp(n + 1, -INF);
    dp[0] = 0;

    SegTree<long long> st(n + 1, -INF);
    st.update(0, 0);

    for (int i = 1; i <= n; ++i) {
        long long max_val = -INF;
        
        // Case: rank k = 0
        // Condition: 0 <= total_exp < b_1  (i.e., total_exp < pb[1])
        // pa[i] - pa[j] < pb[1]  =>  pa[j] > pa[i] - pb[1]
        long long pa_j_lower_bound_k0;
        if (m > 0) {
            pa_j_lower_bound_k0 = pa[i] - pb[1];
        } else {
            pa_j_lower_bound_k0 = -1; 
        }

        auto it_k0_lower = upper_bound(pa.begin(), pa.begin() + i, pa_j_lower_bound_k0);
        int j_k0_lower = distance(pa.begin(), it_k0_lower);
        long long max_dp_k0 = st.query(j_k0_lower, i - 1);

        if (max_dp_k0 > -INF) {
            max_val = max(max_val, 0 + max_dp_k0);
        }
        
        // Case: rank k = 1 to m
        for (int k = 1; k <= m; ++k) {
            // Condition: pb[k] <= total_exp < pb[k+1]
            // pb[k] <= pa[i] - pa[j] < pb[k+1]
            // pa[i] - pb[k+1] < pa[j] <= pa[i] - pb[k]
            
            long long upper_pa_j = pa[i] - pb[k];
            
            auto it_upper = upper_bound(pa.begin(), pa.begin() + i, upper_pa_j);
            int j_upper = distance(pa.begin(), it_upper) - 1;

            long long lower_pa_j_bound = (k < m) ? (pa[i] - pb[k + 1]) : -1;
            auto it_lower = upper_bound(pa.begin(), pa.begin() + i, lower_pa_j_bound);
            int j_lower = distance(pa.begin(), it_lower);

            if (j_lower <= j_upper) {
                long long max_dp_j = st.query(j_lower, j_upper);
                if (max_dp_j > -INF) {
                    max_val = max(max_val, (long long)k + max_dp_j);
                }
            }
        }
        
        if (max_val > -INF) {
            dp[i] = max_val - c;
        }
        
        st.update(i, dp[i]);
    }

    cout << dp[n] << "\n";
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