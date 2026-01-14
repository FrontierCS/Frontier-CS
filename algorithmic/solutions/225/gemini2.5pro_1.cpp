#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

int n, q;
int a[4097];
int pos[4097];

struct Operation {
    int u, v;
};

vector<Operation> ops;
int cnt;

map<vector<int>, int> build_memo;

int build_from_sorted_values(const vector<int>& values) {
    if (values.empty()) {
        return 0;
    }
    if (values.size() == 1) {
        return pos[values[0]];
    }
    auto it = build_memo.find(values);
    if (it != build_memo.end()) {
        return it->second;
    }

    int mid = values.size() / 2;
    vector<int> left_vals(values.begin(), values.begin() + mid);
    vector<int> right_vals(values.begin() + mid, values.end());

    int u = build_from_sorted_values(left_vals);
    int v = build_from_sorted_values(right_vals);
    
    cnt++;
    ops.push_back({u, v});
    return build_memo[values] = cnt;
}

map<pair<int, int>, int> precomputed_set_ids;

void precompute(int L, int R) {
    if (L == R) {
        precomputed_set_ids[{L, R}] = L;
        return;
    }

    int M = L + (R - L) / 2;
    precompute(L, M);
    precompute(M + 1, R);

    vector<int> suffix_vals;
    for (int i = M; i >= L; --i) {
        auto it = lower_bound(suffix_vals.begin(), suffix_vals.end(), a[i]);
        suffix_vals.insert(it, a[i]);
        precomputed_set_ids[{i, M}] = build_from_sorted_values(suffix_vals);
    }
    
    vector<int> prefix_vals;
    for (int j = M + 1; j <= R; ++j) {
        auto it = lower_bound(prefix_vals.begin(), prefix_vals.end(), a[j]);
        prefix_vals.insert(it, a[j]);
        precomputed_set_ids[{M + 1, j}] = build_from_sorted_values(prefix_vals);
    }
}

int get_query_set_id(int l, int r) {
    if (precomputed_set_ids.count({l, r})) {
        return precomputed_set_ids[{l, r}];
    }

    int L = 1, R = n;
    int M = 0;
    while (L <= R) {
        M = L + (R - L) / 2;
        if (l <= M && r > M) {
            break;
        }
        if (r <= M) {
            R = M - 1;
        } else {
            L = M + 1;
        }
    }
    
    vector<int> merged_vals;
    merged_vals.reserve(r - l + 1);
    for(int i = l; i <= r; ++i) {
        merged_vals.push_back(a[i]);
    }
    sort(merged_vals.begin(), merged_vals.end());
    
    return precomputed_set_ids[{l, r}] = build_from_sorted_values(merged_vals);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> q;
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }

    cnt = n;

    precompute(1, n);

    vector<int> ans(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        ans[i] = get_query_set_id(l, r);
    }

    cout << cnt << "\n";
    for (const auto& op : ops) {
        cout << op.u << " " << op.v << "\n";
    }

    for (int i = 0; i < q; ++i) {
        cout << ans[i] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";

    return 0;
}