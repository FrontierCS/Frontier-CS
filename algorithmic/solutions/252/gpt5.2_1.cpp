#include <bits/stdc++.h>
using namespace std;

static int n;

static int ask_range(int u, int k, int l, int r) {
    int m = r - l;
    cout << "? " << u << " " << k << " " << m;
    for (int x = l; x < r; ++x) cout << " " << x;
    cout << endl;

    int resp;
    if (!(cin >> resp)) exit(0);
    if (resp == -1) exit(0);
    return resp;
}

static int find_dest(int u) {
    int l = 1, r = n + 1;
    while (r - l > 1) {
        int mid = (l + r) / 2;
        int resp = ask_range(u, 1, l, mid); // is a[u] in [l, mid)?
        if (resp == 1) r = mid;
        else l = mid;
    }
    return l;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    vector<int> a(n + 1, 1);
    for (int i = 1; i <= n; ++i) a[i] = find_dest(i);

    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; ++i) rev[a[i]].push_back(i);

    vector<int> idx(n + 1, -1);
    vector<int> order;
    int u = 1;
    while (idx[u] == -1) {
        idx[u] = (int)order.size();
        order.push_back(u);
        u = a[u];
    }
    int cycStart = idx[u];
    vector<int> cycleNodes(order.begin() + cycStart, order.end());

    vector<char> inComp(n + 1, 0);
    queue<int> q;
    for (int v : cycleNodes) {
        if (!inComp[v]) {
            inComp[v] = 1;
            q.push(v);
        }
    }
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        for (int p : rev[v]) {
            if (!inComp[p]) {
                inComp[p] = 1;
                q.push(p);
            }
        }
    }

    vector<int> ans;
    for (int i = 1; i <= n; ++i) if (inComp[i]) ans.push_back(i);

    cout << "! " << ans.size();
    for (int v : ans) cout << " " << v;
    cout << endl;

    return 0;
}