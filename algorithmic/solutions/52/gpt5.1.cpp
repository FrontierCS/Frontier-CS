#include <bits/stdc++.h>
using namespace std;

int ask(int l, int r) {
    cout << "1 " << l << " " << r << endl;
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long l1, l2;
    if (!(cin >> n >> l1 >> l2)) return 0;

    if (n == 1) {
        cout << "3 1" << endl;
        return 0;
    }

    vector<int> suffix(n + 2, 0);
    // Suffix queries: segments in [i, n]
    for (int i = n; i >= 1; --i) {
        suffix[i] = ask(i, n);
    }

    // Number of neighbors to the right for each position
    vector<int> R(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        int deltaR = suffix[i] - (i == n ? 0 : suffix[i + 1]);
        R[i] = 1 - deltaR; // 0, 1 or 2
    }

    // Build adjacency graph: vertices are positions, edges connect positions
    // whose values are consecutive integers.
    vector<vector<int>> adj(n + 1);

    for (int i = 1; i <= n; ++i) {
        int Ri = R[i];
        if (Ri == 0) continue;

        // Function F(x) = segments(i, x) - segments(i + 1, x)
        auto F = [&](int x) -> int {
            int s1 = ask(i, x);
            int s2 = ask(i + 1, x);
            return s1 - s2;
        };

        // Find first right neighbor j1
        int lo = i + 1, hi = n, ans1 = n;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            int f = F(mid);
            if (f <= 0) {
                ans1 = mid;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        int j1 = ans1;
        adj[i].push_back(j1);
        adj[j1].push_back(i);

        if (Ri == 2) {
            // Find second right neighbor j2 > j1
            lo = j1 + 1;
            hi = n;
            int ans2 = n;
            while (lo <= hi) {
                int mid = (lo + hi) / 2;
                int f = F(mid);
                if (f < 0) {
                    ans2 = mid;
                    hi = mid - 1;
                } else {
                    lo = mid + 1;
                }
            }
            int j2 = ans2;
            adj[i].push_back(j2);
            adj[j2].push_back(i);
        }
    }

    // Reconstruct the path (order of positions along value-line)
    int start = 1;
    while (start <= n && adj[start].size() != 1) ++start;
    if (start > n) start = 1; // fallback, should not happen

    vector<int> path;
    path.reserve(n);
    int prev = 0, curr = start;
    while (true) {
        path.push_back(curr);
        int next = -1;
        for (int to : adj[curr]) {
            if (to != prev) {
                next = to;
                break;
            }
        }
        if (next == -1) break;
        prev = curr;
        curr = next;
    }

    // Assign values 1..n along the reconstructed path
    vector<int> val(n + 1, 0);
    for (int idx = 0; idx < (int)path.size(); ++idx) {
        val[path[idx]] = idx + 1;
    }
    // If, for some reason, path did not cover all vertices, assign defaults (should not occur)
    for (int i = 1; i <= n; ++i) {
        if (val[i] == 0) val[i] = 1;
    }

    cout << "3";
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << val[i];
    }
    cout << endl;

    return 0;
}