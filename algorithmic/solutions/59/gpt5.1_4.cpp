#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> b;
    long long x;
    while (cin >> x) b.push_back(x);

    vector<int> result(n + 1);

    if ((int)b.size() >= n) {
        vector<int> seq(n + 1);
        for (int i = 0; i < n; ++i) seq[i + 1] = (int)b[i];

        bool is_perm = true;
        vector<int> seen(n + 1, 0);
        for (int i = 1; i <= n; ++i) {
            if (seq[i] < 1 || seq[i] > n || seen[seq[i]]) {
                is_perm = false;
                break;
            }
            seen[seq[i]] = 1;
        }

        bool is_ops = true;
        for (int i = 1; i <= n; ++i) {
            int lo = i;
            int hi = min(n, i + 2);
            if (seq[i] < lo || seq[i] > hi) {
                is_ops = false;
                break;
            }
        }

        if (is_ops && !is_perm) {
            vector<int> arr(n + 1);
            for (int i = 1; i <= n; ++i) arr[i] = i;
            for (int i = 1; i <= n; ++i) {
                int j = seq[i];
                if (j >= 1 && j <= n) swap(arr[i], arr[j]);
            }
            for (int i = 1; i <= n; ++i) result[i] = arr[i];
        } else if (is_perm && !is_ops) {
            for (int i = 1; i <= n; ++i) result[i] = seq[i];
        } else if (is_perm && is_ops) {
            for (int i = 1; i <= n; ++i) result[i] = seq[i];
        } else {
            for (int i = 1; i <= n; ++i) result[i] = seq[i];
        }
    } else {
        for (int i = 1; i <= n; ++i) result[i] = i;
    }

    for (int i = 1; i <= n; ++i) {
        if (i > 1) cout << ' ';
        cout << result[i];
    }
    cout << '\n';

    return 0;
}