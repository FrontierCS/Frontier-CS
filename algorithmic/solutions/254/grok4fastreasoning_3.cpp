#include <bits/stdc++.h>
using namespace std;

int find_max(const vector<int>& orig_C, int n, int m, set<int>& selected, vector<int>& bad_count, vector<vector<int>>& beaten_by) {
    set<int> orig_set(orig_C.begin(), orig_C.end());
    vector<int> current = orig_C;
    set<int> internal_losers_set;
    if (current.empty()) {
        assert(false);
        return -1;
    }
    if (current.size() == 1) return current[0];
    while (current.size() > 1) {
        int s = current.size();
        int num_groups = (s + n - 1) / n;
        vector<int> next_current;
        for (int g = 0; g < num_groups; g++) {
            vector<int> group;
            int start = g * n;
            for (int j = 0; j < n && start + j < s; j++) {
                group.push_back(current[start + j]);
            }
            int gs = group.size();
            int needed = n - gs;
            if (needed > 0) {
                for (int np = 0; np < needed; np++) {
                    bool got = false;
                    for (int p = 1; p <= m && !got; p++) {
                        bool is_in_group = false;
                        for (auto x : group) {
                            if (x == p) {
                                is_in_group = true;
                                break;
                            }
                        }
                        if (selected.find(p) != selected.end()) continue;
                        if (!is_in_group && (orig_set.find(p) == orig_set.end() || internal_losers_set.find(p) != internal_losers_set.end())) {
                            group.push_back(p);
                            got = true;
                        }
                    }
                    assert(got);
                }
            }
            // query
            cout << "?";
            for (auto x : group) cout << " " << x;
            cout << endl;
            cout.flush();
            int winner;
            cin >> winner;
            assert(find(group.begin(), group.end(), winner) != group.end());
            // update
            for (auto l : group) {
                if (l != winner) {
                    beaten_by[winner].push_back(l);
                    bad_count[l]++;
                    internal_losers_set.insert(l);
                }
            }
            next_current.push_back(winner);
        }
        current = next_current;
    }
    return current[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int m = n * n;
        int kk = m - n + 1;
        set<int> selected;
        vector<int> bad_count(m + 1, 0);
        vector<vector<int>> beaten_by(m + 1);
        vector<int> found;
        for (int ii = 0; ii < kk; ii++) {
            vector<int> cand;
            for (int p = 1; p <= m; p++) {
                if (selected.find(p) == selected.end() && bad_count[p] == 0) {
                    cand.push_back(p);
                }
            }
            int nextw = find_max(cand, n, m, selected, bad_count, beaten_by);
            found.push_back(nextw);
            selected.insert(nextw);
            // promote
            for (auto l : beaten_by[nextw]) {
                if (selected.find(l) == selected.end()) {
                    bad_count[l]--;
                }
            }
        }
        cout << "!";
        for (auto p : found) cout << " " << p;
        cout << endl;
        cout.flush();
    }
    return 0;
}