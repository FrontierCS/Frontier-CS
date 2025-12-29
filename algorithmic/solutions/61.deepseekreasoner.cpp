#include <bits/stdc++.h>
using namespace std;
using ll = long long;

const ll INF = -1e18;

struct SegmentTree {
    int n;
    vector<ll> tree;
    SegmentTree(int size) {
        n = size;
        tree.assign(4 * n, INF);
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
    ll query() {
        return tree[1];
    }
};

void solve() {
    int n, m;
    ll c;
    cin >> n >> m >> c;
    vector<ll> a(n + 1);
    for (int i = 1; i <= n; i++) {
        cin >> a[i];
    }
    vector<ll> b(m + 1);
    for (int i = 1; i <= m; i++) {
        cin >> b[i];
    }

    // prefix sums
    vector<ll> A(n + 1);
    for (int i = 1; i <= n; i++) {
        A[i] = A[i - 1] + a[i];
    }
    vector<ll> B(m + 1);
    for (int i = 1; i <= m; i++) {
        B[i] = B[i - 1] + b[i];
    }

    // thresholds: th[i] = B[i+1] for i=0..m-1
    vector<ll> th(m);
    int zero_count = 0;
    for (int i = 0; i < m; i++) {
        th[i] = B[i + 1];
        if (th[i] == 0) zero_count++;
    }

    // dp array
    vector<ll> dp(n + 1);
    dp[0] = 0;

    // bucket for each level (0..m)
    vector<int> bucket(n + 1);
    vector<priority_queue<pair<ll, int>>> pq(m + 1);
    vector<ll> current_max(m + 1, INF);
    SegmentTree seg(m + 1); // stores level + max_dp in that bucket

    auto cleanBucket = [&](int v) {
        while (!pq[v].empty()) {
            auto [val, j] = pq[v].top();
            if (bucket[j] != v || dp[j] != val) {
                pq[v].pop();
            } else {
                break;
            }
        }
        ll new_max = pq[v].empty() ? INF : pq[v].top().first;
        if (current_max[v] != new_max) {
            current_max[v] = new_max;
            seg.update(v, (new_max == INF ? INF : v + new_max));
        }
    };

    // events: (time, j)
    priority_queue<pair<ll, int>, vector<pair<ll, int>>, greater<pair<ll, int>>> events;

    // initialize with j=0
    bucket[0] = zero_count;
    pq[zero_count].push({dp[0], 0});
    cleanBucket(zero_count);
    if (zero_count < m) {
        events.push({A[0] + th[zero_count], 0});
    }

    for (int i = 1; i <= n; i++) {
        ll t = A[i];
        // process events with time <= t
        while (!events.empty() && events.top().first <= t) {
            auto [time, j] = events.top();
            events.pop();
            int v = bucket[j];
            // remove j from bucket v
            cleanBucket(v); // this updates max if j was top
            // move to bucket v+1
            int v_new = v + 1;
            bucket[j] = v_new;
            pq[v_new].push({dp[j], j});
            cleanBucket(v_new);
            // schedule next event if any
            if (v_new < m) {
                events.push({A[j] + th[v_new], j});
            }
        }

        // get global max
        ll M = seg.query();
        dp[i] = M - c;

        // insert new j = i
        int v0 = zero_count;
        bucket[i] = v0;
        pq[v0].push({dp[i], i});
        cleanBucket(v0);
        if (v0 < m) {
            events.push({A[i] + th[v0], i});
        }
    }

    cout << dp[n] << '\n';
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