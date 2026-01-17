#include <bits/stdc++.h>
using namespace std;

const int MAXN = 4200; // 2^12 = 4096
const int LOG = 13;    // log2(MAXN) + 1

int n, q;
int a[MAXN];
int pos[MAXN];           // position of value v
int init_id[MAXN];       // initial set ID for value v (its index)

// Sparse tables for range minimum and maximum
int st_min[LOG][MAXN], st_max[LOG][MAXN];
int log2_[MAXN];

void build_rmq() {
    log2_[1] = 0;
    for (int i = 2; i <= n; i++)
        log2_[i] = log2_[i / 2] + 1;

    for (int i = 1; i <= n; i++) {
        st_min[0][i] = a[i];
        st_max[0][i] = a[i];
    }

    for (int k = 1; k < LOG; k++) {
        int len = 1 << k;
        for (int i = 1; i + len - 1 <= n; i++) {
            st_min[k][i] = min(st_min[k - 1][i], st_min[k - 1][i + len / 2]);
            st_max[k][i] = max(st_max[k - 1][i], st_max[k - 1][i + len / 2]);
        }
    }
}

int range_min(int l, int r) {
    int k = log2_[r - l + 1];
    return min(st_min[k][l], st_min[k][r - (1 << k) + 1]);
}

int range_max(int l, int r) {
    int k = log2_[r - l + 1];
    return max(st_max[k][l], st_max[k][r - (1 << k) + 1]);
}

int cnt;                         // current number of sets
vector<pair<int, int>> ops;      // merge operations
map<pair<int, int>, int> interval_id; // memoization for intervals
map<vector<int>, int> sorted_id; // memoization for sorted sets

// Build a sorted set from a sorted list of values (recursively)
int build_sorted(const vector<int>& vals, int l, int r) {
    if (l == r) {
        return init_id[vals[l]]; // singleton set for that value
    }
    int mid = (l + r) / 2;
    int id1 = build_sorted(vals, l, mid);
    int id2 = build_sorted(vals, mid + 1, r);
    ops.push_back({id1, id2});
    ++cnt;
    return cnt;
}

// Get the set ID for index interval [l, r]
int get_interval(int l, int r) {
    if (l == r) return l; // initial set S_l
    auto key = make_pair(l, r);
    if (interval_id.count(key)) return interval_id[key];

    // Try to find a split point where max(left) < min(right)
    for (int m = l; m < r; ++m) {
        if (range_max(l, m) < range_min(m + 1, r)) {
            int id1 = get_interval(l, m);
            int id2 = get_interval(m + 1, r);
            ops.push_back({id1, id2});
            ++cnt;
            interval_id[key] = cnt;
            return cnt;
        }
    }

    // No valid split -> build sorted set of all values in [l, r]
    vector<int> vals;
    for (int i = l; i <= r; ++i)
        vals.push_back(a[i]);
    sort(vals.begin(), vals.end());

    if (sorted_id.count(vals)) {
        interval_id[key] = sorted_id[vals];
        return sorted_id[vals];
    }

    // Build the sorted set recursively
    int id = build_sorted(vals, 0, (int)vals.size() - 1);
    sorted_id[vals] = id;
    interval_id[key] = id;
    return id;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n >> q;
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
        init_id[a[i]] = i; // set ID for value a[i] is its index i
    }

    build_rmq();

    cnt = n; // start with n sets
    vector<int> query_ids(q);

    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        query_ids[i] = get_interval(l, r);
    }

    // Output
    cout << cnt << "\n";
    for (auto& op : ops)
        cout << op.first << " " << op.second << "\n";
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << query_ids[i];
    }
    cout << "\n";

    return 0;
}