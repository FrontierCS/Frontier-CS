#include <bits/stdc++.h>
using namespace std;

static bool build_with_color(const vector<string>& g, vector<int> arr, int initColor, vector<int>& out) {
    int n = (int)arr.size();
    vector<int> p = arr;
    bool changed = false;
    int cur = initColor;
    for (int i = 0; i < n - 1; ++i) {
        char want = char('0' + cur);
        int j = i + 1;
        while (j < n && g[p[i]-1][p[j]-1] != want) ++j;
        if (j == n) {
            if (changed) return false;
            changed = true;
            cur ^= 1;
            want = char('0' + cur);
            j = i + 1;
            while (j < n && g[p[i]-1][p[j]-1] != want) ++j;
            if (j == n) return false;
        }
        int val = p[j];
        for (int k = j; k > i + 1; --k) p[k] = p[k - 1];
        p[i + 1] = val;
    }

    // Build edges and determine rotation to ensure at most one change among first n-1 comparisons
    vector<char> e(n);
    for (int i = 0; i < n - 1; ++i) e[i] = g[p[i]-1][p[i+1]-1];
    e[n-1] = g[p[n-1]-1][p[0]-1];

    vector<int> chg;
    for (int i = 0; i < n; ++i) {
        if (e[i] != e[(i + 1) % n]) chg.push_back(i);
    }

    int start = 0;
    if (!chg.empty()) start = (chg[0] + 1) % n;

    vector<int> res(n);
    for (int k = 0; k < n; ++k) res[k] = p[(start + k) % n];

    // Validate
    vector<char> ec(n);
    for (int i = 0; i < n - 1; ++i) ec[i] = g[res[i]-1][res[i+1]-1];
    ec[n-1] = g[res[n-1]-1][res[0]-1];
    int diff = 0;
    for (int i = 0; i < n - 1; ++i) if (ec[i] != ec[i + 1]) ++diff;
    if (diff <= 1) {
        out = move(res);
        return true;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    while ( (cin >> n) ) {
        vector<string> g(n, string(n, '0'));
        for (int i = 0; i < n; ++i) {
            int cnt = 0;
            while (cnt < n) {
                string s;
                cin >> s;
                for (char ch : s) {
                    if (ch == '0' || ch == '1') {
                        g[i][cnt++] = ch;
                        if (cnt == n) break;
                    }
                }
            }
        }

        vector<int> base(n);
        iota(base.begin(), base.end(), 1);
        vector<int> rev = base;
        reverse(rev.begin(), rev.end());

        vector<vector<int>> arrs;
        arrs.push_back(base);
        arrs.push_back(rev);

        // Additional deterministic rotations to increase robustness
        int add = min(n, 10);
        for (int k = 1; k <= add; ++k) {
            vector<int> rot(n);
            for (int i = 0; i < n; ++i) rot[i] = base[(i + k) % n];
            arrs.push_back(rot);
        }

        bool done = false;
        vector<int> ans;
        for (auto& arr : arrs) {
            for (int c = 0; c <= 1; ++c) {
                vector<int> out;
                if (build_with_color(g, arr, c, out)) {
                    ans = move(out);
                    done = true;
                    break;
                }
            }
            if (done) break;
        }

        if (!done) {
            // As a last resort, try a few more rotations of reversed order
            int add2 = min(n, 10);
            for (int k = 1; k <= add2 && !done; ++k) {
                vector<int> rot(n);
                for (int i = 0; i < n; ++i) rot[i] = rev[(i + k) % n];
                for (int c = 0; c <= 1; ++c) {
                    vector<int> out;
                    if (build_with_color(g, rot, c, out)) {
                        ans = move(out);
                        done = true;
                        break;
                    }
                }
            }
        }

        if (!done) {
            // Fallback (should rarely happen); print -1 as per statement, though solution should always exist.
            cout << -1 << '\n';
        } else {
            for (int i = 0; i < n; ++i) {
                if (i) cout << ' ';
                cout << ans[i];
            }
            cout << '\n';
        }
    }
    return 0;
}