#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

int n, t;
vector<int> adj[MAXN];
int parentArr[MAXN], depthArr[MAXN];
int tin[MAXN], tout[MAXN], timerDFS;
int cntSub[MAXN];
bool inP[MAXN];

void dfsInit(int u, int p) {
    parentArr[u] = p;
    depthArr[u] = (p == 0 ? 0 : depthArr[p] + 1);
    tin[u] = ++timerDFS;
    for (int v : adj[u]) {
        if (v == p) continue;
        dfsInit(v, u);
    }
    tout[u] = timerDFS;
}

void dfsCount(int u, int p) {
    cntSub[u] = inP[u] ? 1 : 0;
    for (int v : adj[u]) {
        if (v == p) continue;
        dfsCount(v, u);
        cntSub[u] += cntSub[v];
    }
}

bool inSubtree(int x, int u) {
    return tin[x] <= tin[u] && tin[u] <= tout[x];
}

int ask(int x) {
    cout << "? " << x << endl;
    cout.flush();
    int ans;
    if (!(cin >> ans)) {
        exit(0);
    }
    if (ans == -1) {
        exit(0);
    }
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> t)) {
        return 0;
    }
    while (t--) {
        cin >> n;
        for (int i = 1; i <= n; ++i) {
            adj[i].clear();
        }
        for (int i = 0; i < n - 1; ++i) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        timerDFS = 0;
        dfsInit(1, 0);

        vector<int> P;
        P.reserve(n);
        for (int i = 1; i <= n; ++i) P.push_back(i);

        int queryCount = 0;

        while (P.size() > 1 && queryCount < 160) {
            // mark current candidates
            for (int i = 1; i <= n; ++i) inP[i] = false;
            for (int u : P) inP[u] = true;

            // compute subtree counts
            dfsCount(1, 0);

            int s = (int)P.size();
            int bestX = -1;
            int bestDiff = INT_MAX;

            for (int v = 1; v <= n; ++v) {
                int k = cntSub[v];
                if (k == 0 || k == s) continue;
                int diff = abs(2 * k - s);
                if (diff < bestDiff) {
                    bestDiff = diff;
                    bestX = v;
                }
            }

            if (bestX == -1) {
                // fallback, should not normally happen unless P.size() == 1
                break;
            }

            int ans = ask(bestX);
            ++queryCount;

            vector<int> Pnew;
            Pnew.reserve(P.size());

            if (ans == 1) {
                for (int u : P) {
                    if (inSubtree(bestX, u)) {
                        Pnew.push_back(u);
                    }
                }
            } else {
                static bool used[MAXN];
                for (int i = 1; i <= n; ++i) used[i] = false;
                for (int u : P) {
                    if (inSubtree(bestX, u)) continue;
                    int v = (u == 1 ? 1 : parentArr[u]);
                    if (!used[v]) {
                        used[v] = true;
                        Pnew.push_back(v);
                    }
                }
            }
            if (!Pnew.empty())
                P.swap(Pnew);
            else {
                // inconsistent, but to avoid issues, break
                break;
            }
        }

        int answer = 1;
        if (!P.empty()) answer = P[0];

        cout << "! " << answer << endl;
        cout.flush();
    }

    return 0;
}