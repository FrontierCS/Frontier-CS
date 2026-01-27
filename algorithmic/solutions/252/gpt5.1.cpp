#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Number of bits needed to encode rooms 1..n
    int B = 0;
    while ((1 << B) <= n) B++;

    // Precompute sets S[b] = { i | (i >> b) & 1 }
    vector<vector<int>> S(B);
    for (int b = 0; b < B; ++b) {
        for (int i = 1; i <= n; ++i) {
            if ((i >> b) & 1) S[b].push_back(i);
        }
    }

    auto query = [&](int u, long long k, int b) -> int {
        const auto &Sb = S[b];
        cout << "? " << u << " " << k << " " << Sb.size();
        for (int v : Sb) cout << " " << v;
        cout << endl;
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        return ans;
    };

    // Recover teleporter mapping a[i]
    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        int id = 0;
        for (int b = 0; b < B; ++b) {
            if (S[b].empty()) continue;
            int ans = query(i, 1, b);
            if (ans == 1) id |= (1 << b);
        }
        if (id < 1) id = 1;
        if (id > n) id = n;
        a[i] = id;
    }

    // Build reverse graph
    vector<vector<int>> rev(n + 1);
    for (int i = 1; i <= n; ++i) {
        rev[a[i]].push_back(i);
    }

    // Forward orbit from 1 (tail + cycle)
    vector<int> in_forward(n + 1, 0);
    vector<int> forward_list;
    int cur = 1;
    while (!in_forward[cur]) {
        in_forward[cur] = 1;
        forward_list.push_back(cur);
        cur = a[cur];
    }

    // BFS on reverse edges from all nodes reachable from 1
    vector<int> inA(n + 1, 0);
    deque<int> dq;
    for (int v : forward_list) {
        if (!inA[v]) {
            inA[v] = 1;
            dq.push_back(v);
        }
    }
    while (!dq.empty()) {
        int v = dq.front();
        dq.pop_front();
        for (int u : rev[v]) {
            if (!inA[u]) {
                inA[u] = 1;
                dq.push_back(u);
            }
        }
    }

    vector<int> A;
    for (int i = 1; i <= n; ++i) {
        if (inA[i]) A.push_back(i);
    }

    cout << "! " << A.size();
    for (int v : A) cout << " " << v;
    cout << endl;
    cout.flush();

    return 0;
}