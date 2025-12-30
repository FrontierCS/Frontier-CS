#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    int i = 1;
    vector<int> others;
    for (int pos = 1; pos <= n; ++pos) {
        if (pos != i) others.push_back(pos);
    }
    vector<pair<int, int>> group_info; // pair<start_idx in others, f>
    int start = 0;
    while (start < others.size()) {
        int mm = min(250, (int)others.size() - start);
        vector<int> seq;
        seq.push_back(i);
        for (int t = 0; t < mm; ++t) {
            int j = others[start + t];
            seq.push_back(j);
            if (t < mm - 1) {
                seq.push_back(i);
                seq.push_back(i);
                seq.push_back(i);
            }
        }
        seq.push_back(i);
        int kk = seq.size();
        cout << "0 " << kk;
        for (int idx : seq) cout << " " << idx;
        cout << endl;
        int ff;
        cin >> ff;
        group_info.emplace_back(start, ff);
        start += mm;
    }
    // find a group with f > 0
    int chosen_group = -1;
    for (int gg = 0; gg < group_info.size(); ++gg) {
        if (group_info[gg].second > 0) {
            chosen_group = gg;
            break;
        }
    }
    assert(chosen_group != -1);
    int g_start = group_info[chosen_group].first;
    int g_f = group_info[chosen_group].second;
    vector<int> current;
    for (int t = 0; t < 250; ++t) {
        if (g_start + t >= others.size()) break;
        current.push_back(others[g_start + t]);
    }
    // binary search to find one j
    while (current.size() > 1) {
        int half = current.size() / 2;
        vector<int> left(current.begin(), current.begin() + half);
        int mleft = left.size();
        if (mleft == 0) {
            current = vector<int>(current.begin() + half, current.end());
            continue;
        }
        vector<int> seq;
        seq.push_back(i);
        for (int t = 0; t < mleft; ++t) {
            int j = left[t];
            seq.push_back(j);
            if (t < mleft - 1) {
                seq.push_back(i);
                seq.push_back(i);
                seq.push_back(i);
            }
        }
        seq.push_back(i);
        int kk = seq.size();
        cout << "0 " << kk;
        for (int idx : seq) cout << " " << idx;
        cout << endl;
        int fleft;
        cin >> fleft;
        if (fleft > 0) {
            current = left;
        } else {
            current = vector<int>(current.begin() + half, current.end());
        }
    }
    int j = current[0];
    // now order query
    cout << "0 2 " << i << " " << j << endl;
    int f_pair;
    cin >> f_pair;
    int open_p = (f_pair == 1 ? i : j);
    int close_p = (f_pair == 1 ? j : i);
    // now the string
    vector<char> ss(n + 1);
    ss[open_p] = '(';
    ss[close_p] = ')';
    // to_test
    vector<int> to_test;
    for (int pos = 1; pos <= n; ++pos) {
        if (pos != open_p && pos != close_p) to_test.push_back(pos);
    }
    int num_g = (to_test.size() + 7) / 8;
    vector<vector<int>> groups(num_g);
    int t_idx = 0;
    for (int g = 0; g < num_g; ++g) {
        int sz = min(8, (int)to_test.size() - t_idx);
        for (int tt = 0; tt < sz; ++tt) {
            groups[g].push_back(to_test[t_idx++]);
        }
    }
    // now test each group
    for (int g = 0; g < num_g; ++g) {
        vector<int> grp = groups[g];
        int sz = grp.size();
        vector<int> seq;
        for (int b = 0; b < sz; ++b) {
            int p = grp[b];
            int r = (1 << b);
            // block
            seq.push_back(open_p);
            seq.push_back(p);
            for (int rr = 1; rr < r; ++rr) {
                seq.push_back(open_p); // extra
                seq.push_back(open_p); // o
                seq.push_back(p);
            }
            // breaker if not last
            if (b < sz - 1) {
                seq.push_back(open_p); // breaker
            }
        }
        int kk = seq.size();
        cout << "0 " << kk;
        for (int id : seq) cout << " " << id;
        cout << endl;
        int ff;
        cin >> ff;
        // decode
        for (int b = 0; b < sz; ++b) {
            if (ff & (1 << b)) {
                ss[grp[b]] = ')';
            } else {
                ss[grp[b]] = '(';
            }
        }
    }
    // output
    cout << "1 ";
    for (int pos = 1; pos <= n; ++pos) {
        cout << ss[pos];
    }
    cout << endl;
    return 0;
}