#include <bits/stdc++.h>
using namespace std;

vector<int> longest_subseq_indices(const vector<int>& candidates, const vector<int>& p, bool decreasing) {
    int m = (int)candidates.size();
    if (m == 0) return {};
    vector<int> tail;
    tail.reserve(m);
    vector<int> tail_pos;
    tail_pos.reserve(m);
    vector<int> prev_pos(m, -1);

    for (int pos = 0; pos < m; ++pos) {
        int val = p[candidates[pos]];
        if (decreasing) val = -val;
        auto it = lower_bound(tail.begin(), tail.end(), val);
        int idx = int(it - tail.begin());
        if (idx == (int)tail.size()) {
            tail.push_back(val);
            tail_pos.push_back(pos);
        } else {
            tail[idx] = val;
            tail_pos[idx] = pos;
        }
        if (idx > 0) prev_pos[pos] = tail_pos[idx - 1];
    }

    int L = (int)tail.size();
    vector<int> seq_pos(L);
    int cur = tail_pos[L - 1];
    for (int i = L - 1; i >= 0; --i) {
        seq_pos[i] = cur;
        cur = prev_pos[cur];
    }

    vector<int> res(L);
    for (int i = 0; i < L; ++i) res[i] = candidates[seq_pos[i]];
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    vector<vector<int>> groups(4);
    vector<char> used(n, false);

    auto assign = [&](int g, bool decreasing) {
        vector<int> candidates;
        candidates.reserve(n);
        for (int i = 0; i < n; ++i)
            if (!used[i]) candidates.push_back(i);
        if (candidates.empty()) return;
        vector<int> chosen = longest_subseq_indices(candidates, p, decreasing);
        for (int idx : chosen) {
            used[idx] = true;
            groups[g].push_back(idx);
        }
    };

    // a: LIS, b: LDS, c: LIS, d: remaining
    assign(0, false);
    assign(1, true);
    assign(2, false);
    for (int i = 0; i < n; ++i)
        if (!used[i]) groups[3].push_back(i);

    cout << groups[0].size() << ' ' << groups[1].size() << ' '
         << groups[2].size() << ' ' << groups[3].size() << '\n';

    for (int g = 0; g < 4; ++g) {
        for (int j = 0; j < (int)groups[g].size(); ++j) {
            if (j) cout << ' ';
            cout << p[groups[g][j]];
        }
        cout << '\n';
    }

    return 0;
}