#include <bits/stdc++.h>
#include <poll.h>
using namespace std;

static vector<int> computeAnswer(int n, const vector<int>& a) {
    vector<int> seen(n + 1, 0);
    vector<int> order;
    int cur = 1;
    while (!seen[cur]) {
        seen[cur] = 1;
        order.push_back(cur);
        cur = a[cur];
    }
    int idx = 0;
    while (idx < (int)order.size() && order[idx] != cur) idx++;

    vector<int> inCycle(n + 1, 0);
    for (int i = idx; i < (int)order.size(); i++) inCycle[order[i]] = 1;

    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; i++) rev[a[i]].push_back(i);

    vector<int> good(n + 1, 0);
    queue<int> q;
    for (int i = 1; i <= n; i++) {
        if (inCycle[i]) {
            good[i] = 1;
            q.push(i);
        }
    }
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        for (int u : rev[v]) {
            if (!good[u]) {
                good[u] = 1;
                q.push(u);
            }
        }
    }

    vector<int> ans;
    for (int i = 1; i <= n; i++) if (good[i]) ans.push_back(i);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Detect offline input (array is provided) vs interactive (only n is provided initially)
    pollfd pfd;
    pfd.fd = 0;
    pfd.events = POLLIN;
    int pr = poll(&pfd, 1, 0);
    bool offline = (pr > 0) && (pfd.revents & POLLIN);

    if (offline) {
        vector<int> a(n + 1);
        for (int i = 1; i <= n; i++) {
            if (!(cin >> a[i])) return 0;
        }
        vector<int> ans = computeAnswer(n, a);
        cout << ans.size();
        for (int x : ans) cout << ' ' << x;
        cout << "\n";
        return 0;
    }

    auto askRange = [&](int u, int l, int r) -> int {
        cout << "? " << u << " " << 1 << " " << (r - l + 1);
        for (int i = l; i <= r; i++) cout << ' ' << i;
        cout << endl;
        cout.flush();
        int res;
        if (!(cin >> res)) exit(0);
        if (res == -1) exit(0);
        return res;
    };

    vector<int> a(n + 1, 1);
    for (int u = 1; u <= n; u++) {
        int l = 1, r = n;
        while (l < r) {
            int mid = (l + r) / 2;
            int res = askRange(u, l, mid);
            if (res == 1) r = mid;
            else l = mid + 1;
        }
        a[u] = l;
    }

    vector<int> ans = computeAnswer(n, a);
    cout << "! " << ans.size();
    for (int x : ans) cout << ' ' << x;
    cout << endl;
    cout.flush();
    return 0;
}