#include <bits/stdc++.h>
using namespace std;

mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());

pair<int,int> query(const vector<int> &v) {
    int k = (int)v.size();
    cout << 0 << " " << k;
    for (int x : v) cout << " " << x;
    cout << endl;
    cout.flush();

    int a, b;
    if (!(cin >> a >> b)) {
        exit(0);
    }
    if (a == -1 && b == -1) exit(0);
    return {a, b};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> cur(n);
    for (int i = 0; i < n; ++i) cur[i] = i + 1;

    // Initial query on all indices to get global medians
    auto g = query(cur);
    int v1 = g.first, v2 = g.second; // v1 < v2

    // Shrink current set until size = 6
    while ((int)cur.size() > 6) {
        int k = (int)cur.size();
        while (true) {
            int a = rng() % k;
            int b = rng() % k;
            if (a == b) continue;
            int idx1 = cur[a];
            int idx2 = cur[b];

            vector<int> S;
            S.reserve(k - 2);
            for (int x : cur) {
                if (x != idx1 && x != idx2) S.push_back(x);
            }

            auto res = query(S);
            if (res.first == v1 && res.second == v2) {
                // Good pair (one low, one high), remove them
                if (a > b) swap(a, b);
                cur.erase(cur.begin() + b);
                cur.erase(cur.begin() + a);
                break;
            }
            // else: bad pair, keep trying
        }
    }

    // Now cur.size() == 6, composition: 2 lows, 2 highs, 2 medians
    vector<int> arr = cur; // size 6
    const int K = 6;
    vector<int> deg(K, 0);

    for (int i = 0; i < K; ++i) {
        for (int j = i + 1; j < K; ++j) {
            vector<int> S;
            S.reserve(4);
            for (int t = 0; t < K; ++t) {
                if (t == i || t == j) continue;
                S.push_back(arr[t]);
            }
            auto res = query(S);
            if (res.first == v1 && res.second == v2) {
                // Pair (arr[i], arr[j]) is (low, high)
                deg[i]++;
                deg[j]++;
            }
        }
    }

    vector<int> ans;
    for (int i = 0; i < K; ++i) {
        if (deg[i] == 0) ans.push_back(arr[i]);
    }

    if (ans.size() < 2) {
        // Fallback (shouldn't happen theoretically)
        while ((int)ans.size() < 2 && !arr.empty()) {
            ans.push_back(arr.back());
            arr.pop_back();
        }
    }

    cout << 1 << " " << ans[0] << " " << ans[1] << endl;
    cout.flush();

    return 0;
}