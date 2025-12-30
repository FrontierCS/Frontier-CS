#include <bits/stdc++.h>
using namespace std;

static void die() {
    exit(0);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        int n;
        cin >> n;
        if (!cin || n == -1) return 0;

        int m = 2 * n - 1;
        int uniqueVal = -1;
        int queries = 0;

        auto askPrefix = [&](int x, int mid) -> int {
            ++queries;
            cout << "? " << x << " " << mid;
            for (int i = 1; i <= mid; i++) cout << " " << i;
            cout << "\n";
            cout.flush();

            int res;
            cin >> res;
            if (!cin || res == -1) die();
            return res;
        };

        auto askRange = [&](int x, int l, int r) -> int {
            if (l > r) return 0;
            int k = r - l + 1;
            ++queries;
            cout << "? " << x << " " << k;
            for (int i = l; i <= r; i++) cout << " " << i;
            cout << "\n";
            cout.flush();

            int res;
            cin >> res;
            if (!cin || res == -1) die();
            return res;
        };

        for (int x = 1; x <= n; x++) {
            int lo = 1, hi = m;
            while (lo < hi) {
                int mid = (lo + hi) / 2;
                int ans = askPrefix(x, mid);
                if (ans) hi = mid;
                else lo = mid + 1;
            }
            int firstPos = lo;
            int hasSecond = (firstPos < m) ? askRange(x, firstPos + 1, m) : 0;
            if (!hasSecond) {
                uniqueVal = x;
                break;
            }
            if (queries > 5000) die();
        }

        if (uniqueVal == -1) uniqueVal = 1;

        cout << "! " << uniqueVal << "\n";
        cout.flush();
    }

    return 0;
}