#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<long long> tokens;
    long long t;
    while (cin >> t) tokens.push_back(t);

    bool mappingOK = (tokens.size() >= (size_t)n);
    vector<int> a(n + 1, 0);

    if (mappingOK) {
        for (int i = 1; i <= n; i++) {
            long long v = tokens[i - 1];
            if (v < 1 || v > n) { mappingOK = false; break; }
            a[i] = (int)v;
        }
    }

    if (mappingOK) {
        vector<vector<int>> radj(n + 1);
        for (int i = 1; i <= n; i++) {
            radj[a[i]].push_back(i);
        }

        vector<char> inOrbit(n + 1, false);
        int u = 1;
        while (!inOrbit[u]) {
            inOrbit[u] = true;
            u = a[u];
        }

        vector<char> reach(n + 1, false);
        deque<int> dq;
        for (int i = 1; i <= n; i++) {
            if (inOrbit[i]) {
                reach[i] = true;
                dq.push_back(i);
            }
        }
        while (!dq.empty()) {
            int v = dq.front(); dq.pop_front();
            for (int p : radj[v]) {
                if (!reach[p]) {
                    reach[p] = true;
                    dq.push_back(p);
                }
            }
        }

        vector<int> A;
        for (int i = 1; i <= n; i++) if (reach[i]) A.push_back(i);
        sort(A.begin(), A.end());

        cout << A.size();
        for (int x : A) cout << " " << x;
        cout << "\n";
    } else {
        cout << "! " << n;
        for (int i = 1; i <= n; i++) cout << " " << i;
        cout << "\n";
    }

    return 0;
}