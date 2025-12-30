#include <bits/stdc++.h>
using namespace std;

static int n, m;
static int queryCount;

static int readResp() {
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

static int ask_interval(int x, int l, int r) {
    ++queryCount;
    cout << "? " << x << " " << (r - l + 1);
    for (int i = l; i <= r; i++) cout << " " << i;
    cout << "\n";
    cout.flush();
    return readResp();
}

static int ask_all_except(int x, int p) {
    ++queryCount;
    cout << "? " << x << " " << (m - 1);
    for (int i = 1; i <= m; i++) if (i != p) cout << " " << i;
    cout << "\n";
    cout.flush();
    return readResp();
}

static int find_one_pos(int x) {
    int l = 1, r = m;
    while (l < r) {
        int mid = (l + r) >> 1;
        int ans = ask_interval(x, l, mid);
        if (ans) r = mid;
        else l = mid + 1;
    }
    return l;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;

    for (int tc = 0; tc < t; tc++) {
        if (!(cin >> n)) return 0;
        if (n == -1) return 0;

        m = 2 * n - 1;
        queryCount = 0;

        int answer = -1;
        for (int x = 1; x <= n; x++) {
            int p = find_one_pos(x);
            int ans = ask_all_except(x, p);
            if (ans == 0) {
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