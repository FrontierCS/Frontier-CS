#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask(int u, int k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << "\n" << flush;

    int ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    vector<int> a(n + 1, 0);

    for (int u = 1; u <= n; u++) {
        int L = 1, R = n;
        while (L < R) {
            int mid = (L + R) >> 1;
            vector<int> S;
            S.reserve(mid - L + 1);
            for (int x = L; x <= mid; x++) S.push_back(x);
            int res = ask(u, 1, S);
            if (res) R = mid;
            else L = mid + 1;
        }
        a[u] = L;
    }

    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; i++) rev[a[i]].push_back(i);

    vector<int> pos(n + 1, -1), order;
    int cur = 1;
    while (pos[cur] == -1) {
        pos[cur] = (int)order.size();
        order.push_back(cur);
        cur = a[cur];
    }
    int start = pos[cur];
    vector<int> inCycle(n + 1, 0);
    for (int i = start; i < (int)order.size(); i++) inCycle[order[i]] = 1;

    vector<int> inA(n + 1, 0);
    queue<int> q;
    for (int i = 1; i <= n; i++) {
        if (inCycle[i]) {
            inA[i] = 1;
            q.push(i);
        }
    }
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int p : rev[v]) {
            if (!inA[p]) {
                inA[p] = 1;
                q.push(p);
            }
        }
    }

    vector<int> A;
    for (int i = 1; i <= n; i++) if (inA[i]) A.push_back(i);

    cout << "! " << A.size();
    for (int x : A) cout << " " << x;
    cout << "\n" << flush;

    return 0;
}