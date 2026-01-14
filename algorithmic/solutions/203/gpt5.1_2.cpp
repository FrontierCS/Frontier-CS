#include <bits/stdc++.h>
using namespace std;

int query(const vector<int> &v) {
    cout << "Query " << v.size();
    for (int x : v) cout << ' ' << x;
    cout << endl;
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    int M = 2 * N;

    vector<int> good;                 // chameleons with pairwise distinct colors, unpaired
    vector<bool> used(M + 1, false);  // already paired chameleons

    int answers_given = 0;

    for (int x = 1; x <= M; ++x) {
        if (used[x]) continue;

        // Check if x has a new color w.r.t current good set
        vector<int> S = good;
        S.push_back(x);
        int ans = query(S);

        if (ans == (int)S.size()) {
            // x has a new color; add to good set
            good.push_back(x);
        } else {
            // x shares color with someone in good; find partner via binary search
            vector<int> cand = good;
            while (cand.size() > 1) {
                int mid = cand.size() / 2;
                vector<int> part(cand.begin(), cand.begin() + mid);
                vector<int> q = part;
                q.push_back(x);
                int res = query(q);
                if (res == (int)q.size()) {
                    // x's partner not in part
                    cand.erase(cand.begin(), cand.begin() + mid);
                } else {
                    // x's partner is in part
                    cand.erase(cand.begin() + mid, cand.end());
                }
            }
            int y = cand[0];

            cout << "Answer " << x << ' ' << y << endl;
            cout.flush();
            ++answers_given;

            used[x] = used[y] = true;

            // remove y from good
            auto it = find(good.begin(), good.end(), y);
            if (it != good.end()) good.erase(it);
        }
    }

    // Ensure exactly N answers (in case some remain unmatched, though algorithm should pair all)
    // If any remain in good (should not happen), pair them arbitrarily to satisfy protocol
    while (answers_given < N && !good.empty()) {
        int a = good.back();
        good.pop_back();
        if (good.empty()) break;
        int b = good.back();
        good.pop_back();
        cout << "Answer " << a << ' ' << b << endl;
        cout.flush();
        ++answers_given;
    }

    return 0;
}