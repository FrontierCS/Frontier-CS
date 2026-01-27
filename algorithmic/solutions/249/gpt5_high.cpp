#include <bits/stdc++.h>
using namespace std;

static mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    auto randint = [&](int l, int r) {
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };

    int s = randint(1, n);
    vector<int> r(n + 1, -1);
    int mVal = INT_MAX;
    vector<int> S;
    S.reserve(n);

    for (int i = 1; i <= n; ++i) {
        if (i == s) continue;
        int val = ask(s, i);
        r[i] = val;
        if (val < mVal) {
            mVal = val;
            S.clear();
            S.push_back(i);
        } else if (val == mVal) {
            S.push_back(i);
        }
    }

    // If already unique candidate
    vector<int> cand = S;

    if (cand.size() > 1) {
        // Build list of t's not in S (i.e., r[t] > mVal), sorted by r[t] ascending
        vector<int> order;
        order.reserve(n);
        for (int i = 1; i <= n; ++i) {
            if (i == s) continue;
            if (r[i] > mVal) order.push_back(i);
        }
        sort(order.begin(), order.end(), [&](int a, int b) {
            return r[a] < r[b];
        });

        // Use t's from 'order' to reduce candidates
        for (int t : order) {
            if (cand.size() <= 1) break;
            int best = INT_MAX;
            vector<int> newc;
            newc.reserve(cand.size());
            for (int c : cand) {
                int v = ask(c, t);
                if (v < best) {
                    best = v;
                    newc.clear();
                    newc.push_back(c);
                } else if (v == best) {
                    newc.push_back(c);
                }
            }
            cand.swap(newc);
        }

        // If still more than 1, fallback to random t's not equal to s and not in cand if possible
        // Limit iterations to a reasonable number
        int tries = 0;
        while (cand.size() > 1 && tries < 200) {
            int t = randint(1, n);
            if (t == s) continue;
            bool inCand = false;
            for (int c : cand) if (c == t) { inCand = true; break; }
            if (inCand) continue; // avoid c == t case since query is invalid
            int best = INT_MAX;
            vector<int> newc;
            newc.reserve(cand.size());
            for (int c : cand) {
                int v = ask(c, t);
                if (v < best) {
                    best = v;
                    newc.clear();
                    newc.push_back(c);
                } else if (v == best) {
                    newc.push_back(c);
                }
            }
            cand.swap(newc);
            ++tries;
        }
    }

    int z = cand[0];
    vector<int> ans(n + 1, 0);
    ans[z] = 0;
    for (int i = 1; i <= n; ++i) {
        if (i == z) continue;
        ans[i] = ask(z, i);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << ans[i];
    cout << endl;
    cout.flush();

    return 0;
}