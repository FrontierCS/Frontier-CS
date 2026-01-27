#include <bits/stdc++.h>
using namespace std;

int find_max(const vector<int>& contestants, int n) {
    int s = contestants.size();
    if (s == 1) return contestants[0];
    set<int> unproc(contestants.begin(), contestants.end());
    set<int> procc;
    // First group
    vector<int> group;
    auto iter = unproc.begin();
    for (int i = 0; i < n; ++i) {
        group.push_back(*iter);
        ++iter;
    }
    // Query
    cout << "?";
    for (int x : group) cout << " " << x;
    cout << endl;
    cout.flush();
    int champion;
    cin >> champion;
    // Update sets
    for (int x : group) {
        unproc.erase(x);
        procc.insert(x);
    }
    // Loop
    while (!unproc.empty()) {
        size_t rem = unproc.size();
        size_t num_new = min((size_t)n - 1, rem);
        size_t num_pads_needed = n - 1 - num_new;
        // Pick new_ones
        vector<int> new_ones;
        iter = unproc.begin();
        for (size_t i = 0; i < num_new; ++i) {
            new_ones.push_back(*iter);
            ++iter;
        }
        // Pick pads
        vector<int> pads;
        if (num_pads_needed > 0) {
            vector<int> possible;
            for (int p : procc) {
                if (p != champion) {
                    possible.push_back(p);
                }
            }
            for (size_t i = 0; i < num_pads_needed; ++i) {
                pads.push_back(possible[i]);
            }
        }
        // Form query group
        vector<int> qgroup = {champion};
        qgroup.insert(qgroup.end(), new_ones.begin(), new_ones.end());
        qgroup.insert(qgroup.end(), pads.begin(), pads.end());
        // Query
        cout << "?";
        for (int x : qgroup) cout << " " << x;
        cout << endl;
        cout.flush();
        int race_winner;
        cin >> race_winner;
        champion = race_winner;
        // Update sets for new_ones
        for (int x : new_ones) {
            unproc.erase(x);
            procc.insert(x);
        }
    }
    return champion;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        int m = n * n;
        vector<int> active;
        for (int i = 1; i <= m; ++i) active.push_back(i);
        vector<int> ordered;
        while (active.size() > n - 1) {
            int maxp = find_max(active, n);
            ordered.push_back(maxp);
            auto it = find(active.begin(), active.end(), maxp);
            active.erase(it);
        }
        // Output answer
        cout << "!";
        for (int p : ordered) cout << " " << p;
        cout << endl;
        cout.flush();
    }
    return 0;
}