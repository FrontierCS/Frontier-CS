#include <bits/stdc++.h>
using namespace std;

static int n;

static int query_race(const vector<int>& a) {
    cout << "?";
    for (int x : a) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    int p;
    if (!(cin >> p)) exit(0);
    if (p == -1) exit(0);
    return p;
}

static void answer_order(const vector<int>& a) {
    cout << "!";
    for (int x : a) cout << ' ' << x;
    cout << '\n';
    cout.flush();
}

static int find_max_in_set(const vector<int>& elems) {
    int m = (int)elems.size();
    if (m == n) {
        vector<int> g(elems.begin(), elems.end());
        return query_race(g);
    }

    vector<int> group;
    group.reserve(n);
    for (int i = 0; i < n; i++) group.push_back(elems[i]);

    int champ = query_race(group);

    vector<int> pool;
    pool.reserve(n - 1);
    for (int x : group) if (x != champ) pool.push_back(x);

    int idx = n;
    while (idx < m) {
        int take = min(n - 1, m - idx);

        vector<int> participants;
        participants.reserve(n);
        participants.push_back(champ);
        for (int i = 0; i < take; i++) participants.push_back(elems[idx + i]);

        int need = (n - 1) - take;
        for (int i = 0; i < need; i++) participants.push_back(pool[i]);

        int win = query_race(participants);
        if (win != champ) {
            champ = win;
            pool.clear();
            for (int x : participants) if (x != champ) pool.push_back(x);
        }
        idx += take;
    }

    return champ;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    while (t--) {
        cin >> n;

        int total = n * n;
        int needFast = total - n + 1;

        vector<int> rem(total);
        iota(rem.begin(), rem.end(), 1);

        vector<int> ans;
        ans.reserve(needFast);

        while ((int)rem.size() > n - 1) {
            int mx = find_max_in_set(rem);
            ans.push_back(mx);

            auto it = find(rem.begin(), rem.end(), mx);
            if (it == rem.end()) exit(0);
            *it = rem.back();
            rem.pop_back();
        }

        answer_order(ans);
    }

    return 0;
}