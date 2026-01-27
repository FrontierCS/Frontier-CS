#include <bits/stdc++.h>
using namespace std;

static int n;

static int query(int u, long long k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << (int)S.size();
    for (int x : S) cout << " " << x;
    cout << "\n";
    cout.flush();

    int ans;
    if (!(cin >> ans)) exit(0);
    return ans;
}

static int find_next_room(int u) {
    int lo = 1, hi = n;
    while (lo < hi) {
        int mid = (lo + hi) / 2;
        vector<int> S;
        S.reserve(mid - lo + 1);
        for (int i = lo; i <= mid; i++) S.push_back(i);

        int ans = query(u, 1, S);
        if (ans == 1) hi = mid;
        else lo = mid + 1;
    }
    return lo;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    vector<int> a(n + 1);
    for (int i = 1; i <= n; i++) a[i] = find_next_room(i);

    vector<int> pos(n + 1, -1), order;
    int cur = 1;
    while (pos[cur] == -1) {
        pos[cur] = (int)order.size();
        order.push_back(cur);
        cur = a[cur];
    }
    int cycleStart = pos[cur];
    vector<int> cycleNodes;
    for (int i = cycleStart; i < (int)order.size(); i++) cycleNodes.push_back(order[i]);

    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; i++) rev[a[i]].push_back(i);

    vector<char> inBasin(n + 1, 0);
    queue<int> q;
    for (int v : cycleNodes) {
        inBasin[v] = 1;
        q.push(v);
    }
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        for (int u : rev[v]) {
            if (!inBasin[u]) {
                inBasin[u] = 1;
                q.push(u);
            }
        }
    }

    vector<int> A;
    for (int i = 1; i <= n; i++) if (inBasin[i]) A.push_back(i);

    cout << "! " << (int)A.size();
    for (int x : A) cout << " " << x;
    cout << "\n";
    cout.flush();
    return 0;
}