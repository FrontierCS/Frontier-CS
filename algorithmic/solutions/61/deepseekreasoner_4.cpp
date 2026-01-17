#include <bits/stdc++.h>
using namespace std;

typedef long long ll;

const ll INF = 1e18;

struct SegmentTree {
    int n;
    vector<ll> tree;
    SegmentTree(int size) {
        n = size;
        tree.assign(4 * n, -INF);
    }
    void update(int idx, int l, int r, int pos, ll val) {
        if (l == r) {
            tree[idx] = val;
            return;
        }
        int mid = (l + r) / 2;
        if (pos <= mid) update(idx * 2, l, mid, pos, val);
        else update(idx * 2 + 1, mid + 1, r, pos, val);
        tree[idx] = max(tree[idx * 2], tree[idx * 2 + 1]);
    }
    void update(int pos, ll val) {
        update(1, 0, n - 1, pos, val);
    }
    ll query(int idx, int l, int r, int ql, int qr) {
        if (qr < l || r < ql) return -INF;
        if (ql <= l && r <= qr) return tree[idx];
        int mid = (l + r) / 2;
        return max(query(idx * 2, l, mid, ql, qr),
                   query(idx * 2 + 1, mid + 1, r, ql, qr));
    }
    ll query(int l, int r) {
        if (l > r) return -INF;
        return query(1, 0, n - 1, l, r);
    }
};

void solve() {
    int n, m;
    ll c;
    cin >> n >> m >> c;
    vector<ll> a(n + 1);
    vector<ll> A(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
        A[i] = A[i - 1] + a[i];
    }
    vector<ll> b(m + 1);
    vector<ll> B_pref(m + 1, 0);
    for (int i = 1; i <= m; i++) {
        cin >> b[i];
        B_pref[i] = B_pref[i - 1] + b[i];
    }
    // compress B_pref[1..m] (thresholds)
    vector<pair<ll, int>> th;
    for (int i = 1; i <= m; i++) {
        if (th.empty() || th.back().first != B_pref[i]) {
            th.emplace_back(B_pref[i], 1);
        } else {
            th.back().second++;
        }
    }
    int m_uniq = th.size();
    vector<ll> U(m_uniq);
    vector<int> cnt(m_uniq);
    for (int i = 0; i < m_uniq; i++) {
        U[i] = th[i].first;
        cnt[i] = th[i].second;
    }

    SegmentTree seg(n + 1);
    // dp[0] = 0, insert j = 0 with value -c
    seg.update(0, -c);
    vector<ll> dp(n + 1, 0);
    vector<int> ptr(m_uniq, 0);
    // A[ptr[u]] is the next candidate for threshold u

    for (int i = 1; i <= n; i++) {
        // process thresholds: include j that satisfy A[j] <= A[i] - U[u]
        for (int u = 0; u < m_uniq; u++) {
            while (ptr[u] < i && A[ptr[u]] <= A[i] - U[u]) {
                int j = ptr[u];
                ll cur = seg.query(j, j);
                seg.update(j, cur + cnt[u]);
                ptr[u]++;
            }
        }
        // get max V[j] for j < i
        ll best = seg.query(0, i - 1);
        dp[i] = best;
        // insert j = i with initial value dp[i] - c
        seg.update(i, dp[i] - c);
    }
    cout << dp[n] << "\n";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}