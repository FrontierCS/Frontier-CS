#include <bits/stdc++.h>
using namespace std;

static int qcnt = 0;

static int ask(const vector<int>& idx) {
    ++qcnt;
    cout << "0 " << idx.size();
    for (int x : idx) cout << " " << x;
    cout << "\n";
    cout.flush();

    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

static bool isMixed(const vector<int>& s) {
    vector<int> q;
    q.reserve(2 * s.size());
    for (int x : s) q.push_back(x);
    for (int i = (int)s.size() - 1; i >= 0; --i) q.push_back(s[i]);
    return ask(q) > 0;
}

static int findOpposite(int a, vector<int> cand) {
    // cand is guaranteed to contain at least one index with bracket != bracket[a]
    while ((int)cand.size() > 1) {
        int mid = (int)cand.size() / 2;
        vector<int> L(cand.begin(), cand.begin() + mid);
        vector<int> R(cand.begin() + mid, cand.end());

        vector<int> u;
        u.reserve(1 + L.size());
        u.push_back(a);
        for (int x : L) u.push_back(x);

        if (isMixed(u)) cand.swap(L);
        else cand.swap(R);
    }
    return cand[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int closeIdx = -1, openIdx = -1;

    vector<int> first;
    for (int i = 1; i <= min(500, n); ++i) first.push_back(i);

    if (isMixed(first)) {
        int a = first[0];
        vector<int> cand(first.begin() + 1, first.end());
        int b = findOpposite(a, cand);

        int v = ask({a, b, a, b});
        if (v == 3) { openIdx = a; closeIdx = b; }
        else if (v == 1) { openIdx = b; closeIdx = a; }
        else exit(0);
    } else {
        // first is uniform; opposite must exist in the remaining indices
        int a = first[0];
        vector<int> second;
        for (int i = (int)first.size() + 1; i <= n; ++i) second.push_back(i);
        int b = findOpposite(a, second);

        int v = ask({a, b, a, b});
        if (v == 3) { openIdx = a; closeIdx = b; }
        else if (v == 1) { openIdx = b; closeIdx = a; }
        else exit(0);
    }

    string ans(n, '?');
    for (int start = 1; start <= n; start += 8) {
        int m = min(8, n - start + 1);
        vector<int> q;
        int sumWeights = (1 << m) - 1;
        q.reserve(3 * sumWeights);

        for (int j = 0; j < m; ++j) {
            int w = 1 << j;
            for (int rep = 0; rep < w; ++rep) {
                q.push_back(closeIdx);
                q.push_back(start + j);
                q.push_back(closeIdx);
            }
        }

        int r = ask(q);
        for (int j = 0; j < m; ++j) {
            ans[start + j - 1] = ((r >> j) & 1) ? '(' : ')';
        }
    }

    cout << "1 " << ans << "\n";
    cout.flush();
    return 0;
}