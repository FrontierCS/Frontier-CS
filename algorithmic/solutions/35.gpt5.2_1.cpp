#include <bits/stdc++.h>
using namespace std;

static int query_segment(int x, int l, int r) {
    int sz = r - l + 1;
    cout << "? " << x << " " << sz;
    for (int i = l; i <= r; ++i) cout << " " << i;
    cout << '\n';
    cout.flush();

    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

static int query_exclude(int x, int p, int m) {
    cout << "? " << x << " " << (m - 1);
    for (int i = 1; i <= m; ++i) if (i != p) cout << " " << i;
    cout << '\n';
    cout.flush();

    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; ++tc) {
        int n;
        cin >> n;
        if (!cin) return 0;
        if (n == -1) return 0;

        int m = 2 * n - 1;
        int uniqueVal = -1;

        for (int x = 1; x <= n; ++x) {
            int l = 1, r = m;
            while (l < r) {
                int mid = (l + r) >> 1;
                int resp = query_segment(x, l, mid);
                if (resp == 1) r = mid;
                else l = mid + 1;
            }
            int p = l;

            int resp2 = query_exclude(x, p, m);
            if (resp2 == 0) {
                uniqueVal = x;
                break;
            }
        }

        if (uniqueVal == -1) uniqueVal = 1; // should never happen

        cout << "! " << uniqueVal << '\n';
        cout.flush();
    }

    return 0;
}