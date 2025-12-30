#include <bits/stdc++.h>
using namespace std;

int n, l1_lim, l2_lim;
vector<vector<int>> cacheAsk;

int ask(int l, int r) {
    if (l > r) return 0;
    if (cacheAsk[l][r] != -1) return cacheAsk[l][r];
    cout << "1 " << l << " " << r << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    cacheAsk[l][r] = x;
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> l1_lim >> l2_lim)) return 0;

    cacheAsk.assign(n + 2, vector<int>(n + 2, -1));

    // Compute Eprefix[r] = number of edges with both endpoints in [1, r]
    vector<int> Eprefix(n + 1, 0);
    for (int r = 1; r <= n; r++) {
        int f = ask(1, r);
        int E = r - f; // E([1, r]) = len - segments
        Eprefix[r] = E;
    }

    vector<int> inc(n + 1, 0);
    inc[1] = Eprefix[1];
    for (int r = 2; r <= n; r++) inc[r] = Eprefix[r] - Eprefix[r - 1];

    auto g = [&](int l, int r) -> int {
        // g(l, r) = number of edges involving r whose other endpoint in [l, r-1]
        // g(l, r) = 1 - f(l, r) + f(l, r-1)
        int fr = ask(l, r);
        int frm1 = ask(l, r - 1);
        return 1 - fr + frm1;
    };

    vector<vector<int>> adj(n + 1);
    for (int r = 1; r <= n; r++) {
        int k = inc[r];
        if (k <= 0) continue;
        // Find the larger neighbor index b: smallest l in [1, r-1] with g(l, r) >= 1
        int lo = 1, hi = r - 1, ans1 = -1;
        while (lo <= hi) {
            int mid = (lo + hi) >> 1;
            int val = g(mid, r);
            if (val >= 1) {
                ans1 = mid;
                hi = mid - 1;
            } else {
                lo = mid + 1;
            }
        }
        if (ans1 != -1) {
            adj[r].push_back(ans1);
            adj[ans1].push_back(r);
        }
        if (k == 2) {
            int lo2 = 1, hi2 = ans1 - 1, ans2 = -1;
            while (lo2 <= hi2) {
                int mid = (lo2 + hi2) >> 1;
                int val = g(mid, r);
                if (val >= 2) {
                    ans2 = mid;
                    hi2 = mid - 1;
                } else {
                    lo2 = mid + 1;
                }
            }
            if (ans2 != -1) {
                adj[r].push_back(ans2);
                adj[ans2].push_back(r);
            }
        }
    }

    // Reconstruct the path order of positions
    vector<int> deg(n + 1, 0);
    for (int i = 1; i <= n; i++) deg[i] = (int)adj[i].size();

    vector<int> order;
    order.reserve(n);
    vector<int> vis(n + 1, 0);

    int start = 1;
    if (n >= 2) {
        for (int i = 1; i <= n; i++) {
            if (deg[i] == 1) {
                start = i;
                break;
            }
        }
    }

    int prev = 0, cur = start;
    for (int step = 0; step < n && cur != 0; step++) {
        order.push_back(cur);
        vis[cur] = 1;
        int nxt = 0;
        for (int x : adj[cur]) if (x != prev && !vis[x]) { nxt = x; break; }
        prev = cur;
        cur = nxt;
    }

    if ((int)order.size() < n) {
        // Try to start from any unvisited endpoint
        for (int i = 1; i <= n && (int)order.size() < n; i++) {
            if (!vis[i] && deg[i] <= 1) {
                prev = 0; cur = i;
                while (cur && !vis[cur]) {
                    order.push_back(cur);
                    vis[cur] = 1;
                    int nxt = 0;
                    for (int x : adj[cur]) if (x != prev && !vis[x]) { nxt = x; break; }
                    prev = cur; cur = nxt;
                }
            }
        }
        // If still missing (cycle case), traverse arbitrarily
        for (int i = 1; i <= n && (int)order.size() < n; i++) {
            if (!vis[i]) {
                prev = 0; cur = i;
                while (!vis[cur]) {
                    order.push_back(cur);
                    vis[cur] = 1;
                    int nxt = 0;
                    for (int x : adj[cur]) if (x != prev) { nxt = x; break; }
                    prev = cur; cur = nxt;
                    if (cur == 0) break;
                }
            }
        }
    }

    // Assign values according to path order (one of two possible permutations)
    vector<int> p(n + 1, 0);
    for (int i = 0; i < n; i++) {
        int idx = order[i];
        p[idx] = i + 1;
    }

    cout << "3";
    for (int i = 1; i <= n; i++) cout << " " << p[i];
    cout << endl;
    cout.flush();
    return 0;
}