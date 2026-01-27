#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(const vector<int>& v) {
    cout << "?";
    for (int x : v) cout << ' ' << x;
    cout << '\n';
    cout.flush();

    int p;
    if (!(cin >> p)) exit(0);
    if (p == -1) exit(0);
    return p;
}

static int find_max_in(const vector<int>& rem) {
    int k = (int)rem.size();
    vector<int> processed;
    processed.reserve(k);

    vector<int> q;
    q.reserve(n);

    for (int i = 0; i < n; i++) q.push_back(rem[i]);
    int champ = ask(q);
    for (int i = 0; i < n; i++) processed.push_back(rem[i]);

    int idx = n;
    while (idx < k) {
        int take = min(n - 1, k - idx);
        q.clear();
        q.push_back(champ);
        for (int i = 0; i < take; i++) q.push_back(rem[idx + i]);

        int need = n - (int)q.size();
        if (need > 0) {
            for (int x : processed) {
                if (x == champ) continue;
                bool used = false;
                for (int y : q) {
                    if (y == x) { used = true; break; }
                }
                if (used) continue;
                q.push_back(x);
                if (--need == 0) break;
            }
        }

        champ = ask(q);
        for (int i = 0; i < take; i++) processed.push_back(rem[idx + i]);
        idx += take;
    }

    return champ;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        cin >> n;
        int N = n * n;
        int need = N - n + 1;

        vector<int> rem(N);
        iota(rem.begin(), rem.end(), 1);

        vector<int> ans;
        ans.reserve(need);

        while ((int)rem.size() > n - 1) {
            int mx = find_max_in(rem);
            ans.push_back(mx);

            auto it = find(rem.begin(), rem.end(), mx);
            if (it == rem.end()) exit(0);
            rem.erase(it);
        }

        cout << "!";
        for (int x : ans) cout << ' ' << x;
        cout << '\n';
        cout.flush();
    }
    return 0;
}