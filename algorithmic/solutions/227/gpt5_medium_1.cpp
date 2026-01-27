#include <bits/stdc++.h>
using namespace std;

vector<int> LIS_indices(const vector<pair<int,int>>& seq, bool useNeg) {
    int m = (int)seq.size();
    vector<int> tail_val;
    vector<int> tail_idx;
    vector<int> prev(m, -1);

    tail_val.reserve(m);
    tail_idx.reserve(m);

    for (int j = 0; j < m; ++j) {
        int x = seq[j].second;
        if (useNeg) x = -x;
        auto it = lower_bound(tail_val.begin(), tail_val.end(), x);
        int k = (int)(it - tail_val.begin());
        if (k == (int)tail_val.size()) {
            tail_val.push_back(x);
            tail_idx.push_back(j);
        } else {
            tail_val[k] = x;
            tail_idx[k] = j;
        }
        if (k > 0) prev[j] = tail_idx[k-1];
    }
    vector<int> res;
    if (tail_idx.empty()) return res;
    int last = tail_idx.back();
    while (last != -1) {
        res.push_back(seq[last].first); // original index
        last = prev[last];
    }
    reverse(res.begin(), res.end());
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<pair<int,int>> allSeq;
    allSeq.reserve(n);
    for (int i = 0; i < n; ++i) allSeq.push_back({i, p[i]});

    // a = LIS of whole sequence
    vector<int> A_idx = LIS_indices(allSeq, false);
    vector<char> used(n, 0);
    for (int idx : A_idx) used[idx] = 1;

    // remaining after removing a
    vector<pair<int,int>> rem1;
    rem1.reserve(n - (int)A_idx.size());
    for (int i = 0; i < n; ++i) if (!used[i]) rem1.push_back({i, p[i]});

    // b = LDS of remaining
    vector<int> B_idx = LIS_indices(rem1, true);
    for (int idx : B_idx) used[idx] = 1;

    // remaining after removing a and b
    vector<pair<int,int>> rem2;
    rem2.reserve(n - (int)A_idx.size() - (int)B_idx.size());
    for (int i = 0; i < n; ++i) if (!used[i]) rem2.push_back({i, p[i]});

    vector<int> C_idx, D_idx;

    if (!rem2.empty()) {
        vector<int> C1 = LIS_indices(rem2, false);
        vector<int> D1 = LIS_indices(rem2, true);

        // Choose larger between LIS and LDS for the third group
        unordered_set<int> chosen;
        chosen.reserve(rem2.size() * 2);

        if (C1.size() >= D1.size()) {
            for (int idx : C1) chosen.insert(idx);
            // c = C1, d = rest
            for (int idx : C1) C_idx.push_back(idx);
            for (auto &pr : rem2) if (!chosen.count(pr.first)) D_idx.push_back(pr.first);
        } else {
            for (int idx : D1) chosen.insert(idx);
            // d = D1, c = rest
            for (int idx : D1) D_idx.push_back(idx);
            for (auto &pr : rem2) if (!chosen.count(pr.first)) C_idx.push_back(pr.first);
        }
    }

    // Build values in original order for each subsequence
    auto sort_by_index = [&](vector<int>& v) {
        sort(v.begin(), v.end());
    };
    sort_by_index(A_idx);
    sort_by_index(B_idx);
    sort_by_index(C_idx);
    sort_by_index(D_idx);

    vector<int> A_vals, B_vals, C_vals, D_vals;
    A_vals.reserve(A_idx.size());
    B_vals.reserve(B_idx.size());
    C_vals.reserve(C_idx.size());
    D_vals.reserve(D_idx.size());

    for (int idx : A_idx) A_vals.push_back(p[idx]);
    for (int idx : B_idx) B_vals.push_back(p[idx]);
    for (int idx : C_idx) C_vals.push_back(p[idx]);
    for (int idx : D_idx) D_vals.push_back(p[idx]);

    cout << (int)A_vals.size() << " " << (int)B_vals.size() << " " << (int)C_vals.size() << " " << (int)D_vals.size() << "\n";

    auto print_seq = [&](const vector<int>& seq) {
        for (size_t i = 0; i < seq.size(); ++i) {
            if (i) cout << " ";
            cout << seq[i];
        }
        cout << "\n";
    };

    print_seq(A_vals);
    print_seq(B_vals);
    print_seq(C_vals);
    print_seq(D_vals);

    return 0;
}