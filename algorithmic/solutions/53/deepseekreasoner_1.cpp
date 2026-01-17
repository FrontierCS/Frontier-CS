#include <bits/stdc++.h>
using namespace std;

int ask(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    int n;
    cin >> n;
    // choose k = 1
    cout << 1 << endl;

    // identity permutation
    vector<int> id(n);
    iota(id.begin(), id.end(), 1);
    int base = ask(id);

    vector<int> p(n + 1, 0);
    // For each position i, we try to find p[i]
    // We'll use binary search on the value of p[i]
    // We'll use a heuristic: place i at position 2, and partition candidates
    // into low and high sets. The answer may indicate whether p[i] is in high set.
    // This is not guaranteed to work for all cases, but is a best effort.

    for (int i = 1; i <= n; i++) {
        if (i == 1) continue; // k=1, we skip i=1 for now, will deduce later
        int l = 1, r = n;
        while (l < r) {
            int mid = (l + r) / 2;
            // Build query q:
            // position 1: some value (ignored)
            // position 2: i
            // positions 3...: first all numbers > mid in increasing order,
            // then all numbers <= mid (except i) in decreasing order.
            vector<int> q(n);
            q[0] = i; // position 1, but k=1 so ignored
            q[1] = i; // position 2
            vector<bool> used(n + 1, false);
            used[i] = true;
            int pos = 2; // start filling from index 2 (0-based)
            // high set: values > mid
            for (int v = mid + 1; v <= n; v++) {
                if (!used[v]) {
                    q[pos++] = v;
                    used[v] = true;
                }
            }
            // low set: values <= mid, except i
            for (int v = mid; v >= 1; v--) {
                if (!used[v]) {
                    q[pos++] = v;
                    used[v] = true;
                }
            }
            // ask query
            int ans = ask(q);
            if (ans > base) {
                // possibly p[i] > mid
                l = mid + 1;
            } else {
                r = mid;
            }
        }
        p[i] = l;
    }

    // Now deduce p[1] from the fact that p is a permutation
    vector<bool> seen(n + 1, false);
    for (int i = 2; i <= n; i++) seen[p[i]] = true;
    for (int i = 1; i <= n; i++) if (!seen[i]) p[1] = i;

    cout << "!";
    for (int i = 1; i <= n; i++) cout << " " << p[i];
    cout << endl;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}