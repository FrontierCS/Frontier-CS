#include <bits/stdc++.h>
using namespace std;

template<typename T>
vector<int> lis_indices_from_subset(const vector<int>& idxs, const vector<T>& vals) {
    int m = (int)idxs.size();
    if (m == 0) return {};
    vector<T> tail_vals;
    vector<int> tail_pos;
    vector<int> prev(m, -1);

    for (int j = 0; j < m; ++j) {
        T v = vals[j];
        int pos = lower_bound(tail_vals.begin(), tail_vals.end(), v) - tail_vals.begin();
        if (pos == (int)tail_vals.size()) {
            tail_vals.push_back(v);
            tail_pos.push_back(j);
        } else {
            tail_vals[pos] = v;
            tail_pos[pos] = j;
        }
        if (pos > 0) prev[j] = tail_pos[pos - 1];
    }

    int L = (int)tail_vals.size();
    if (L == 0) return {};
    int j = tail_pos[L - 1];
    vector<int> res(L);
    for (int k = L - 1; k >= 0; --k) {
        res[k] = idxs[j];
        j = prev[j];
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> perm(n);
    for (int i = 0; i < n; ++i) cin >> perm[i];

    vector<int> group(n, -1); // 0:a (LIS), 1:b (LDS), 2:c (LIS), 3:d (LDS)
    vector<char> used(n, 0);

    // Step 1: LIS for group a
    {
        vector<int> idxs(n);
        iota(idxs.begin(), idxs.end(), 0);
        vector<long long> vals(n);
        for (int i = 0; i < n; ++i) vals[i] = (long long)perm[idxs[i]];
        vector<int> inc1 = lis_indices_from_subset(idxs, vals);
        for (int i : inc1) {
            group[i] = 0;
            used[i] = 1;
        }
    }
    // Step 2: LDS for group d (by LIS on negatives)
    {
        vector<int> idxs;
        for (int i = 0; i < n; ++i) if (!used[i]) idxs.push_back(i);
        vector<long long> vals;
        vals.reserve(idxs.size());
        for (int i : idxs) vals.push_back(-(long long)perm[i]);
        vector<int> dec1 = lis_indices_from_subset(idxs, vals);
        for (int i : dec1) {
            group[i] = 3;
            used[i] = 1;
        }
    }
    // Step 3: LIS for group c
    {
        vector<int> idxs;
        for (int i = 0; i < n; ++i) if (!used[i]) idxs.push_back(i);
        vector<long long> vals;
        vals.reserve(idxs.size());
        for (int i : idxs) vals.push_back((long long)perm[i]);
        vector<int> inc2 = lis_indices_from_subset(idxs, vals);
        for (int i : inc2) {
            group[i] = 2;
            used[i] = 1;
        }
    }
    // Step 4: LDS for group b (by LIS on negatives)
    {
        vector<int> idxs;
        for (int i = 0; i < n; ++i) if (!used[i]) idxs.push_back(i);
        vector<long long> vals;
        vals.reserve(idxs.size());
        for (int i : idxs) vals.push_back(-(long long)perm[i]);
        vector<int> dec2 = lis_indices_from_subset(idxs, vals);
        for (int i : dec2) {
            group[i] = 1;
            used[i] = 1;
        }
    }
    // Assign any remaining to group d
    for (int i = 0; i < n; ++i) if (group[i] == -1) group[i] = 3;

    vector<int> a, b, c, d;
    a.reserve(n); b.reserve(n); c.reserve(n); d.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (group[i] == 0) a.push_back(perm[i]);
        else if (group[i] == 1) b.push_back(perm[i]);
        else if (group[i] == 2) c.push_back(perm[i]);
        else d.push_back(perm[i]);
    }

    cout << (int)a.size() << " " << (int)b.size() << " " << (int)c.size() << " " << (int)d.size() << "\n";
    for (int i = 0; i < (int)a.size(); ++i) {
        if (i) cout << ' ';
        cout << a[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)b.size(); ++i) {
        if (i) cout << ' ';
        cout << b[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)c.size(); ++i) {
        if (i) cout << ' ';
        cout << c[i];
    }
    cout << "\n";
    for (int i = 0; i < (int)d.size(); ++i) {
        if (i) cout << ' ';
        cout << d[i];
    }
    cout << "\n";

    return 0;
}