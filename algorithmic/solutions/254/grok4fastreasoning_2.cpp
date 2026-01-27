#include <bits/stdc++.h>
using namespace std;

int n, m;
vector<vector<int>> direct_losers;

int find_max(vector<int> candidates, int anchor) {
    int s = candidates.size();
    if (s == 1) return candidates[0];
    if (s <= n) {
        if (s == n) {
            // query
            cout << "?";
            for (int x : candidates) cout << " " << x;
            cout << endl;
            cout.flush();
            int w;
            cin >> w;
            // record losers
            for (int x : candidates) {
                if (x != w) direct_losers[w].push_back(x);
            }
            return w;
        } else {
            // 1 < s < n, special race
            // pick fillers from direct_losers[anchor]
            int num_fill = n - s;
            vector<int> fillers;
            set<int> seen;
            set<int> cand_set(candidates.begin(), candidates.end());
            for (int loser : direct_losers[anchor]) {
                if (seen.count(loser)) continue;
                seen.insert(loser);
                if (cand_set.count(loser)) continue;
                fillers.push_back(loser);
                if ((int)fillers.size() == num_fill) break;
            }
            // assume enough
            vector<int> group = candidates;
            group.insert(group.end(), fillers.begin(), fillers.end());
            // query
            cout << "?";
            for (int x : group) cout << " " << x;
            cout << endl;
            cout.flush();
            int w;
            cin >> w;
            // record losers
            for (int x : group) {
                if (x != w) direct_losers[w].push_back(x);
            }
            return w;
        }
    }
    // s > n
    int num_full = s / n;
    int idx = 0;
    vector<int> locals;
    for (int g = 0; g < num_full; ++g) {
        vector<int> group;
        for (int j = 0; j < n; ++j) {
            group.push_back(candidates[idx++]);
        }
        // query
        cout << "?";
        for (int x : group) cout << " " << x;
        cout << endl;
        cout.flush();
        int w;
        cin >> w;
        locals.push_back(w);
        // record losers
        for (int x : group) {
            if (x != w) direct_losers[w].push_back(x);
        }
    }
    vector<int> rem_r;
    for (int i = idx; i < s; ++i) {
        rem_r.push_back(candidates[i]);
    }
    int sub_anchor = -1;
    if (!locals.empty()) sub_anchor = locals[0];
    if (rem_r.empty()) {
        return find_max(locals, sub_anchor);
    } else {
        vector<int> next_level = locals;
        next_level.insert(next_level.end(), rem_r.begin(), rem_r.end());
        return find_max(next_level, sub_anchor);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        cin >> n;
        m = n * n;
        direct_losers.assign(m + 1, {});
        set<int> remaining;
        for (int i = 1; i <= m; ++i) remaining.insert(i);
        vector<int> order;
        while (remaining.size() > n - 1) {
            vector<int> curr(remaining.begin(), remaining.end());
            int maxp = find_max(curr, -1);
            order.push_back(maxp);
            remaining.erase(maxp);
        }
        cout << "!";
        for (int p : order) cout << " " << p;
        cout << endl;
        cout.flush();
    }
    return 0;
}