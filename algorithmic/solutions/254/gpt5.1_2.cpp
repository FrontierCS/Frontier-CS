#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int N = n * n;

        vector<vector<int>> adj(N + 1);
        vector<int> indeg(N + 1, 0);

        vector<int> alive(N);
        iota(alive.begin(), alive.end(), 1);

        while ((int)alive.size() > 1) {
            int m = (int)alive.size();
            if (m < n) break; // Should not happen for N = n^2

            vector<int> R;
            R.reserve(n);
            for (int i = 0; i < n; ++i) {
                R.push_back(alive[i]);
            }

            cout << "?";
            for (int id : R) cout << " " << id;
            cout << endl;
            cout.flush();

            int w;
            if (!(cin >> w)) return 0;
            if (w == -1) return 0;

            vector<char> inR(N + 1, 0);
            for (int id : R) inR[id] = 1;

            vector<int> newAlive;
            newAlive.reserve(m - (n - 1));
            for (int x : alive) {
                if (inR[x] && x != w) {
                    adj[w].push_back(x);
                    ++indeg[x];
                } else {
                    newAlive.push_back(x);
                }
            }
            alive.swap(newAlive);
        }

        queue<int> q;
        for (int i = 1; i <= N; ++i) {
            if (indeg[i] == 0) q.push(i);
        }

        vector<int> order;
        order.reserve(N);
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            order.push_back(u);
            for (int v : adj[u]) {
                if (--indeg[v] == 0) q.push(v);
            }
        }

        int K = N - n + 1;
        cout << "!";
        for (int i = 0; i < K; ++i) {
            cout << " " << order[i];
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}