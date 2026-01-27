#include <bits/stdc++.h>
using namespace std;

pair<int, vector<int>> find_max(const vector<int>& S_in, int n, int m, set<int>& unplaced) {
    vector<int> S = S_in;
    int s = S.size();
    if (s == 0) assert(false);
    if (s == 1) {
        return {S[0], {}};
    }
    vector<int> direct;
    int maxp;
    set<int> S_set(S.begin(), S.end());
    if (s <= n) {
        int need = n - s;
        vector<int> pads;
        vector<int> avail;
        for (int p : unplaced) {
            if (S_set.count(p) == 0) avail.push_back(p);
        }
        assert((int)avail.size() >= need);
        for (int i = 0; i < need; i++) {
            pads.push_back(avail[i]);
        }
        vector<int> race_group = S;
        race_group.insert(race_group.end(), pads.begin(), pads.end());
        cout << "?";
        for (int p : race_group) cout << " " << p;
        cout << endl;
        cout.flush();
        int win;
        cin >> win;
        assert(S_set.count(win));
        maxp = win;
        for (int p : S) {
            if (p != win) direct.push_back(p);
        }
    } else {
        assert(s <= 2 * n - 1);
        vector<int> first_group(S.begin(), S.begin() + n);
        cout << "?";
        for (int p : first_group) cout << " " << p;
        cout << endl;
        cout.flush();
        int m1;
        cin >> m1;
        set<int> first_set(first_group.begin(), first_group.end());
        vector<int> unraced;
        for (int p : S) {
            if (first_set.count(p) == 0) unraced.push_back(p);
        }
        int ur = unraced.size();
        int t = ur + 1;
        int need_pad = n - t;
        vector<int> pads2;
        if (need_pad > 0) {
            vector<int> avail2;
            for (int p : unplaced) {
                if (S_set.count(p) == 0) avail2.push_back(p);
            }
            assert((int)avail2.size() >= need_pad);
            for (int i = 0; i < need_pad; i++) {
                pads2.push_back(avail2[i]);
            }
        }
        vector<int> second_group = unraced;
        second_group.push_back(m1);
        second_group.insert(second_group.end(), pads2.begin(), pads2.end());
        cout << "?";
        for (int p : second_group) cout << " " << p;
        cout << endl;
        cout.flush();
        int m2;
        cin >> m2;
        set<int> unraced_set(unraced.begin(), unraced.end());
        if (m2 == m1) {
            maxp = m1;
            for (int p : first_group) {
                if (p != m1) direct.push_back(p);
            }
            for (int p : unraced) {
                direct.push_back(p);
            }
        } else {
            maxp = m2;
            set<int> second_S_set = unraced_set;
            second_S_set.insert(m1);
            for (int p : second_group) {
                if (p != m2 && second_S_set.count(p)) direct.push_back(p);
            }
        }
    }
    sort(direct.begin(), direct.end());
    auto it = unique(direct.begin(), direct.end());
    direct.resize(it - direct.begin());
    return {maxp, direct};
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
        int k = m - n + 1;
        set<int> unplaced;
        for (int i = 1; i <= m; i++) unplaced.insert(i);
        vector<vector<int>> groups(n, vector<int>(n));
        vector<int> group_winners(n);
        for (int i = 0; i < n; i++) {
            for (int j = 0; j < n; j++) {
                groups[i][j] = i * n + j + 1;
            }
            cout << "?";
            for (int p : groups[i]) cout << " " << p;
            cout << endl;
            cout.flush();
            cin >> group_winners[i];
        }
        cout << "?";
        for (int w : group_winners) cout << " " << w;
        cout << endl;
        cout.flush();
        int M1;
        cin >> M1;
        int orig_group = (M1 - 1) / n;
        vector<int> initial_direct;
        for (int j = 0; j < n; j++) {
            int p = orig_group * n + j + 1;
            if (p != M1) initial_direct.push_back(p);
        }
        for (int i = 0; i < n; i++) {
            if (group_winners[i] != M1) initial_direct.push_back(group_winners[i]);
        }
        vector<int> ordered = {M1};
        unplaced.erase(M1);
        set<int> current_C(initial_direct.begin(), initial_direct.end());
        for (int i = 1; i < k; i++) {
            vector<int> SS(current_C.begin(), current_C.end());
            auto [mp, dir] = find_max(SS, n, m, unplaced);
            ordered.push_back(mp);
            unplaced.erase(mp);
            current_C.clear();
            for (int p : dir) current_C.insert(p);
        }
        cout << "!";
        for (int p : ordered) cout << " " << p;
        cout << endl;
        cout.flush();
    }
    return 0;
}