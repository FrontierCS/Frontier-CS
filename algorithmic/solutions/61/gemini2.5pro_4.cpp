#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

using ll = long long;

const ll INF = 4e18; 

template<typename T>
struct SegTree {
    int n;
    vector<T> t;
    T default_value = -INF;

    SegTree(int n) : n(n), t(4 * n, default_value) {}

    T query(int v, int tl, int tr, int l, int r) {
        if (l > r) {
            return default_value;
        }
        if (l == tl && r == tr) {
            return t[v];
        }
        int tm = tl + (tr - tl) / 2;
        return max(query(v * 2, tl, tm, l, min(r, tm)),
                   query(v * 2 + 1, tm + 1, tr, max(l, tm + 1), r));
    }

    T query(int l, int r) {
        if (l < 0 || r >= n || l > r) return default_value;
        return query(1, 0, n - 1, l, r);
    }

    void update(int v, int tl, int tr, int pos, T new_val) {
        if (tl == tr) {
            t[v] = max(t[v], new_val);
            return;
        }
        int tm = tl + (tr - tl) / 2;
        if (pos <= tm) {
            update(v * 2, tl, tm, pos, new_val);
        } else {
            update(v * 2 + 1, tm + 1, tr, pos, new_val);
        }
        t[v] = max(t[v * 2], t[v * 2 + 1]);
    }

    void update(int pos, T new_val) {
        if (pos < 0 || pos >= n) return;
        update(1, 0, n - 1, pos, new_val);
    }
};

void solve() {
    int n, m;
    ll c;
    cin >> n >> m >> c;
    vector<ll> a(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }
    vector<ll> b(m);
    for (int i = 0; i < m; ++i) {
        cin >> b[i];
    }

    vector<ll> pa(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pa[i + 1] = pa[i] + a[i];
    }

    vector<ll> pb(m + 1, 0);
    for (int i = 0; i < m; ++i) {
        pb[i + 1] = pb[i] + b[i];
    }
    
    vector<ll> pa_unique = pa;
    sort(pa_unique.begin(), pa_unique.end());
    pa_unique.erase(unique(pa_unique.begin(), pa_unique.end()), pa_unique.end());
    
    map<ll, int> pa_ranks;
    for(size_t i = 0; i < pa_unique.size(); ++i) {
        pa_ranks[pa_unique[i]] = i;
    }

    int compressed_size = pa_unique.size();
    SegTree<ll> st(compressed_size);

    vector<ll> dp(n + 1, -INF);
    dp[0] = 0;
    st.update(pa_ranks[pa[0]], dp[0]);

    for (int i = 1; i <= n; ++i) {
        ll max_val = -INF;
        
        for (int k = 0; k <= m; ++k) {
            ll target = pa[i] - pb[k];
            
            auto it = upper_bound(pa_unique.begin(), pa_unique.end(), target);
            if (it == pa_unique.begin()) {
                continue;
            }
            int rank_end = distance(pa_unique.begin(), it) - 1;
            
            ll max_dp_prefix = st.query(0, rank_end);

            if (max_dp_prefix > -INF) {
                max_val = max(max_val, (ll)k + max_dp_prefix);
            }
        }

        if (max_val > -INF) {
            dp[i] = max_val - c;
        }
        st.update(pa_ranks[pa[i]], dp[i]);
    }

    cout << dp[n] << endl;
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