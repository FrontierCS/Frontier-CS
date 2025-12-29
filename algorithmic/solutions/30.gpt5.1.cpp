#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

int n;
vector<int> g[MAXN];
int parentArr[MAXN], depthArr[MAXN];
int tin[MAXN], tout[MAXN], timer_dfs;

void dfs_init(int u, int p) {
    parentArr[u] = (p == 0 ? 1 : p);
    tin[u] = ++timer_dfs;
    for (int v : g[u]) {
        if (v == p) continue;
        depthArr[v] = depthArr[u] + 1;
        dfs_init(v, u);
    }
    tout[u] = timer_dfs;
}

int subSum[MAXN];
int weightNode[MAXN];

void dfs_sub(int u, int p) {
    subSum[u] = weightNode[u];
    for (int v : g[u]) {
        if (v == p) continue;
        dfs_sub(v, u);
        subSum[u] += subSum[v];
    }
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

        timer_dfs = 0;
        depthArr[1] = 0;
        dfs_init(1, 0);

        static bool alive[MAXN];
        static int curPos[MAXN];

        for (int i = 1; i <= n; ++i) {
            alive[i] = true;
            curPos[i] = i;
        }

        int queryCnt = 0;

        while (true) {
            vector<int> cand;
            cand.reserve(n);
            for (int v = 1; v <= n; ++v)
                if (alive[v]) cand.push_back(v);

            if (cand.empty()) {
                cout << "! " << 1 << '\n' << flush;
                break;
            }

            for (int i = 1; i <= n; ++i) weightNode[i] = 0;
            int distinctPos = 0, lastPos = -1;

            for (int v : cand) {
                int p = curPos[v];
                if (weightNode[p] == 0) {
                    ++distinctPos;
                    lastPos = p;
                }
                ++weightNode[p];
            }

            if (distinctPos == 1 || queryCnt >= 160) {
                int ansNode = lastPos;
                if (ansNode == -1) ansNode = 1;
                cout << "! " << ansNode << '\n' << flush;
                break;
            }

            dfs_sub(1, 0);
            int totalCand = (int)cand.size();

            long long bestVal = (long long)totalCand + 5;
            int bestX = 1;

            for (int u = 1; u <= n; ++u) {
                if (subSum[u] == 0 || subSum[u] == totalCand) continue;
                long long a = subSum[u];
                long long b = totalCand - a;
                long long cur = (a > b ? a : b);
                if (cur < bestVal) {
                    bestVal = cur;
                    bestX = u;
                }
            }

            if (bestVal == (long long)totalCand + 5) {
                for (int u = 1; u <= n; ++u) {
                    if (subSum[u] > 0 && subSum[u] < totalCand) {
                        bestX = u;
                        break;
                    }
                }
                if ((subSum[bestX] == 0 || subSum[bestX] == totalCand) && lastPos != -1) {
                    bestX = lastPos;
                }
            }

            cout << "? " << bestX << '\n' << flush;
            int ans;
            if (!(cin >> ans)) return 0;
            ++queryCnt;

            for (int v : cand) {
                int p = curPos[v];
                bool inside = (tin[bestX] <= tin[p] && tin[p] <= tout[bestX]);
                if (ans == 1) {
                    if (!inside) alive[v] = false;
                } else {
                    if (inside) {
                        alive[v] = false;
                    } else {
                        if (p != 1) curPos[v] = parentArr[p];
                    }
                }
            }
        }
    }
    return 0;
}