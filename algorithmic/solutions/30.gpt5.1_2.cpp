#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

int n;
vector<int> g[MAXN];
int parent_arr[MAXN], depth_arr[MAXN];
int tin[MAXN], tout[MAXN], euler[MAXN], timer_dfs;

void dfs(int u, int p) {
    parent_arr[u] = p;
    depth_arr[u] = (p == 0 ? 0 : depth_arr[p] + 1);
    tin[u] = ++timer_dfs;
    euler[timer_dfs] = u;
    for (int v : g[u]) {
        if (v == p) continue;
        dfs(v, u);
    }
    tout[u] = timer_dfs;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        cin >> n;
        for (int i = 1; i <= n; ++i) g[i].clear();

        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        timer_dfs = 0;
        dfs(1, 0);

        vector<int> cand;
        cand.reserve(n);
        vector<char> active(n + 1, 0), newActive(n + 1, 0);

        for (int i = 1; i <= n; ++i) {
            active[i] = 1;
            cand.push_back(i);
        }

        int queriesUsed = 0;

        while (true) {
            int tot = (int)cand.size();
            if (tot == 1 || queriesUsed >= 160) {
                int ans = cand[0];
                cout << "! " << ans << '\n';
                cout.flush();
                break;
            }

            // build prefix sums of active over euler tour
            static int pref[MAXN];
            pref[0] = 0;
            for (int i = 1; i <= n; ++i) {
                int u = euler[i];
                pref[i] = pref[i - 1] + (active[u] ? 1 : 0);
            }
            int TOT = pref[n];

            int bestX = 1;
            int bestW = TOT + 1;

            for (int v = 1; v <= n; ++v) {
                int s1 = pref[tout[v]] - pref[tin[v] - 1];
                int s0 = TOT - s1;
                int w = (s1 > s0 ? s1 : s0);
                if (w < bestW || (w == bestW && depth_arr[v] > depth_arr[bestX])) {
                    bestW = w;
                    bestX = v;
                }
            }

            cout << "? " << bestX << '\n';
            cout.flush();
            int r;
            if (!(cin >> r)) return 0;
            if (r == -1) return 0;
            ++queriesUsed;

            fill(newActive.begin(), newActive.end(), 0);
            vector<int> newCand;
            newCand.reserve(cand.size());

            if (r == 1) {
                for (int v : cand) {
                    if (tin[bestX] <= tin[v] && tin[v] <= tout[bestX]) {
                        if (!newActive[v]) {
                            newActive[v] = 1;
                            newCand.push_back(v);
                        }
                    }
                }
            } else { // r == 0
                for (int v : cand) {
                    if (tin[bestX] <= tin[v] && tin[v] <= tout[bestX]) continue;
                    int u = (v == 1 ? 1 : parent_arr[v]);
                    if (!newActive[u]) {
                        newActive[u] = 1;
                        newCand.push_back(u);
                    }
                }
            }

            cand.swap(newCand);
            active.swap(newActive);
        }
    }

    return 0;
}