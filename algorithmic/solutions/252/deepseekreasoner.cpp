#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <cmath>
#include <cassert>

using namespace std;

bool query(int u, long long k, const vector<int>& S) {
    cout << "? " << u << " " << k << " " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    return res == 1;
}

int main() {
    int n;
    cin >> n;

    vector<int> nxt(n + 1); // teleporter destination from i

    // Find successor for each room u
    for (int u = 1; u <= n; ++u) {
        vector<int> candidates(n);
        for (int i = 0; i < n; ++i) candidates[i] = i + 1;

        while (candidates.size() > 1) {
            int mid = candidates.size() / 2;
            vector<int> left(candidates.begin(), candidates.begin() + mid);
            vector<int> right(candidates.begin() + mid, candidates.end());

            bool inLeft = query(u, 1, left);
            if (inLeft) {
                candidates = move(left);
            } else {
                candidates = move(right);
            }
        }
        nxt[u] = candidates[0];
    }

    // Build reverse graph
    vector<vector<int>> rev(n + 1);
    for (int u = 1; u <= n; ++u) {
        rev[nxt[u]].push_back(u);
    }

    // BFS on reverse graph from room 1 to find the whole component
    vector<bool> vis(n + 1, false);
    queue<int> q;
    q.push(1);
    vis[1] = true;
    while (!q.empty()) {
        int v = q.front(); q.pop();
        for (int u : rev[v]) {
            if (!vis[u]) {
                vis[u] = true;
                q.push(u);
            }
        }
    }

    // Output answer
    vector<int> ans;
    for (int i = 1; i <= n; ++i) if (vis[i]) ans.push_back(i);
    cout << "! " << ans.size();
    for (int x : ans) cout << " " << x;
    cout << endl;
    cout.flush();

    return 0;
}