#include <bits/stdc++.h>
using namespace std;

static int n, m;
static long long qcnt;

static int readInt() {
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

static int askRange(int x, int l, int r) {
    int sz = r - l + 1;
    cout << "? " << x << " " << sz;
    for (int i = l; i <= r; ++i) cout << " " << i;
    cout << "\n";
    cout.flush();
    ++qcnt;

    int res = readInt();
    if (res == -1) exit(0);
    return res;
}

static int askExclude(int x, int pos) {
    int sz = m - 1;
    cout << "? " << x << " " << sz;
    for (int i = 1; i <= m; ++i) if (i != pos) cout << " " << i;
    cout << "\n";
    cout.flush();
    ++qcnt;

    int res = readInt();
    if (res == -1) exit(0);
    return res;
}

static int locateAnyPos(int x) {
    int l = 1, r = m;
    while (l < r) {
        int mid = (l + r) >> 1;
        int res = askRange(x, l, mid);
        if (res == 1) r = mid;
        else l = mid + 1;
    }
    return l;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 1; tc <= t; ++tc) {
        int nn = readInt();
        if (nn == -1) return 0;
        n = nn;
        m = 2 * n - 1;
        qcnt = 0;

        if (m == 1) {
            cout << "! 1\n";
            cout.flush();
            continue;
        }

        int answer = -1;
        for (int x = 1; x <= n; ++x) {
            int pos = locateAnyPos(x);
            int hasOther = askExclude(x, pos);
            if (hasOther == 0) {
                answer = x;
                break;
            }
        }

        if (answer == -1) answer = 1; // should never happen
        cout << "! " << answer << "\n";
        cout.flush();
    }
    return 0;
}