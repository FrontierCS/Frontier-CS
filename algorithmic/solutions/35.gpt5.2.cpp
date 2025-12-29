#include <bits/stdc++.h>
using namespace std;

static int qcount = 0;
static int m_global = 0;

static int askRange(int x, int l, int r) {
    if (l > r) return 0; // avoid empty queries
    ++qcount;
    cout << "? " << x << " " << (r - l + 1);
    for (int i = l; i <= r; ++i) cout << " " << i;
    cout << "\n";
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

    for (int tc = 1; tc <= t; ++tc) {
        int n;
        cin >> n;
        if (!cin) return 0;
        if (n == -1) return 0;

        int m = 2 * n - 1;
        m_global = m;
        qcount = 0;

        int answer = -1;

        for (int x = 1; x <= n; ++x) {
            int lo = 1, hi = m;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                int res = askRange(x, 1, mid);
                if (res == 1) hi = mid;
                else lo = mid + 1;
            }
            int pos = lo;

            bool hasSecond = false;
            if (pos < m) {
                int res = askRange(x, pos + 1, m);
                hasSecond = (res == 1);
            }
            if (!hasSecond) {
                answer = x;
                break;
            }
            if (qcount > 5000) return 0;
        }

        if (answer == -1) answer = 1; // should never happen
        cout << "! " << answer << "\n";
        cout.flush();
    }
    return 0;
}