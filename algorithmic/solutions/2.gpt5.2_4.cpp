#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask_query(const vector<int>& q) {
    cout << 0;
    for (int i = 0; i < n; i++) cout << ' ' << q[i];
    cout << '\n';
    cout.flush();

    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << 1 << ' ' << 1 << '\n';
        cout.flush();
        return 0;
    }

    vector<int> q(n, 1);

    int pos1 = -1, pos2 = -1;

    // Find position of value 1 (anchor). Also may discover position of value 2.
    for (int i = 1; i <= n; i++) {
        fill(q.begin(), q.end(), 1);
        q[i - 1] = 2;
        int ans = ask_query(q);
        if (ans == 0) {
            pos1 = i;
            break;
        }
        if (ans == 2) pos2 = i;
    }

    vector<int> perm(n + 1, 0);
    perm[pos1] = 1;

    vector<int> remaining;
    remaining.reserve(n - 1);
    for (int i = 1; i <= n; i++) {
        if (i != pos1) remaining.push_back(i);
    }

    int startValue = 2;
    if (pos2 != -1) {
        perm[pos2] = 2;
        auto it = find(remaining.begin(), remaining.end(), pos2);
        if (it != remaining.end()) remaining.erase(it);
        startValue = 3;
    }

    for (int v = startValue; v <= n; v++) {
        if (remaining.size() == 1) {
            perm[remaining[0]] = v;
            remaining.clear();
            break;
        }

        int l = 0, r = (int)remaining.size();
        while (r - l > 1) {
            int mid = (l + r) / 2;
            fill(q.begin(), q.end(), 1);
            for (int idx = l; idx < mid; idx++) q[remaining[idx] - 1] = v;
            int ans = ask_query(q);
            if (ans == 2) r = mid;
            else l = mid;
        }

        int pos = remaining[l];
        perm[pos] = v;
        remaining.erase(remaining.begin() + l);
    }

    cout << 1;
    for (int i = 1; i <= n; i++) cout << ' ' << perm[i];
    cout << '\n';
    cout.flush();
    return 0;
}