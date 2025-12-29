#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

vector<int> g[MAXN];
int parentArr[MAXN], depthArr[MAXN];
int tin[MAXN], tout[MAXN], timer_;
int n;

void dfs(int v, int p) {
    parentArr[v] = p;
    tin[v] = ++timer_;
    for (int to : g[v]) {
        if (to == p) continue;
        depthArr[to] = depthArr[v] + 1;
        dfs(to, v);
    }
    tout[v] = timer_;
}

inline bool isAncestor(int u, int v) { // u is ancestor of v
    return tin[u] <= tin[v] && tout[v] <= tout[u];
}

int ask(int x, int &queries) {
    ++queries;
    cout << "? " << x << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (queries > 160) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        cin >> n;
        for (int i = 1; i <= n; ++i) {
            g[i].clear();
        }
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            g[u].push_back(v);
            g[v].push_back(u);
        }

        timer_ = 0;
        depthArr[1] = 0;
        dfs(1, 0);

        vector<int> candidates;
        candidates.reserve(n);
        for (int i = 1; i <= n; ++i) candidates.push_back(i);

        int queries = 0;

        if (n == 1) {
            cout << "! 1" << endl;
            cout.flush();
            continue;
        }

        static int arr[MAXN], pref[MAXN];
        static bool used[MAXN];

        while (true) {
            if (candidates.size() == 1) {
                int ans = candidates[0];
                cout << "! " << ans << endl;
                cout.flush();
                break;
            }

            // Build frequency array over DFS order
            for (int i = 1; i <= n; ++i) arr[i] = 0;
            for (int v : candidates) {
                arr[tin[v]] += 1;
            }
            pref[0] = 0;
            for (int i = 1; i <= n; ++i) pref[i] = pref[i - 1] + arr[i];

            int total = (int)candidates.size();
            int bestX = 1;
            int bestScore = -1;

            for (int x = 1; x <= n; ++x) {
                int c1 = pref[tout[x]] - pref[tin[x] - 1];
                int c0 = total - c1;
                int score = min(c1, c0);
                if (score > bestScore) {
                    bestScore = score;
                    bestX = x;
                }
            }

            if (bestScore <= 0) {
                bestX = candidates[0];
            }

            int r = ask(bestX, queries);

            vector<int> newCandidates;
            newCandidates.reserve(candidates.size());
            for (int i = 1; i <= n; ++i) used[i] = false;

            for (int pos : candidates) {
                bool inside = isAncestor(bestX, pos);
                int expected = inside ? 1 : 0;
                if (expected != r) continue;
                if (!inside && pos != 1) pos = parentArr[pos];
                if (!used[pos]) {
                    used[pos] = true;
                    newCandidates.push_back(pos);
                }
            }

            candidates.swap(newCandidates);

            if (candidates.empty()) {
                // Should not happen if logic is correct; exit to avoid infinite loop.
                exit(0);
            }
        }
    }

    return 0;
}