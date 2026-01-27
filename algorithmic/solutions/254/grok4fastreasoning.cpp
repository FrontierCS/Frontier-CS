#include <bits/stdc++.h>
using namespace std;

int find_max(vector<int> C, const vector<int>& pads, int n, vector<vector<int>>& defeaters) {
    int s = C.size();
    if (s == 1) return C[0];
    if (s < n) {
        int need = n - s;
        vector<int> group = C;
        for (int j = 0; j < need; ++j) {
            group.push_back(pads[j]);
        }
        cout << "?";
        for (int x : group) cout << " " << x;
        cout << endl;
        cout.flush();
        int p;
        cin >> p;
        for (int x : group) {
            if (x != p) defeaters[x].push_back(p);
        }
        return p;
    } else {
        set<int> beaten_set;
        vector<int> all_elements = C;
        // first group
        vector<int> group(all_elements.begin(), all_elements.begin() + n);
        cout << "?";
        for (int x : group) cout << " " << x;
        cout << endl;
        cout.flush();
        int champ;
        cin >> champ;
        for (int x : group) {
            if (x != champ) {
                defeaters[x].push_back(champ);
                beaten_set.insert(x);
            }
        }
        all_elements.erase(all_elements.begin(), all_elements.begin() + n);
        while (!all_elements.empty()) {
            int r = all_elements.size();
            int num_new = min(r, n - 1);
            vector<int> new_ones(all_elements.begin(), all_elements.begin() + num_new);
            vector<int> group_chall;
            group_chall.push_back(champ);
            for (int x : new_ones) group_chall.push_back(x);
            int need_pad = n - (1 + num_new);
            if (need_pad > 0) {
                auto it = beaten_set.begin();
                for (int j = 0; j < need_pad; ++j, ++it) {
                    group_chall.push_back(*it);
                }
            }
            cout << "?";
            for (int x : group_chall) cout << " " << x;
            cout << endl;
            cout.flush();
            int winner;
            cin >> winner;
            for (int x : group_chall) {
                if (x != winner) {
                    defeaters[x].push_back(winner);
                    beaten_set.insert(x);
                }
            }
            champ = winner;
            all_elements.erase(all_elements.begin(), all_elements.begin() + num_new);
        }
        return champ;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    srand(time(NULL));
    int t;
    cin >> t;
    for (int test = 0; test < t; ++test) {
        int n;
        cin >> n;
        int m = n * n;
        int kk = m - n + 1;
        vector<vector<int>> defeaters(m + 1);
        vector<bool> is_top(m + 1, false);
        vector<int> order;
        for (int ii = 0; ii < kk; ++ii) {
            vector<int> C;
            for (int x = 1; x <= m; ++x) {
                if (is_top[x]) continue;
                bool ok = true;
                for (int d : defeaters[x]) {
                    if (!is_top[d]) {
                        ok = false;
                        break;
                    }
                }
                if (ok) C.push_back(x);
            }
            random_shuffle(C.begin(), C.end());
            vector<int> pads;
            unordered_set<int> cand(C.begin(), C.end());
            for (int x = 1; x <= m; ++x) {
                if (!is_top[x] && cand.count(x) == 0) pads.push_back(x);
            }
            int np = find_max(C, pads, n, defeaters);
            order.push_back(np);
            is_top[np] = true;
        }
        cout << "!";
        for (int p : order) cout << " " << p;
        cout << endl;
        cout.flush();
    }
    return 0;
}