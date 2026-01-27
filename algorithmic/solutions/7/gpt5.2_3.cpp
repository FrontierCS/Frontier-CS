#include <bits/stdc++.h>
using namespace std;

struct State {
    int pos;
    int tl;
    int tr;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int L, R;
    cin >> L >> R;

    int B = 0;
    while ((1 << B) <= R) B++;
    if (B == 0) B = 1;

    vector<int> Lb(B), Rb(B);
    for (int i = 0; i < B; i++) {
        int sh = B - 1 - i;
        Lb[i] = (L >> sh) & 1;
        Rb[i] = (R >> sh) & 1;
    }

    static bool canDP[25][2][2];
    for (int tl = 0; tl < 2; tl++)
        for (int tr = 0; tr < 2; tr++)
            canDP[B][tl][tr] = true;

    for (int i = B - 1; i >= 0; i--) {
        for (int tl = 0; tl < 2; tl++) {
            for (int tr = 0; tr < 2; tr++) {
                bool ok = false;
                for (int b = 0; b <= 1; b++) {
                    if (tl && b < Lb[i]) continue;
                    if (tr && b > Rb[i]) continue;
                    int ntl = tl && (b == Lb[i]);
                    int ntr = tr && (b == Rb[i]);
                    if (canDP[i + 1][ntl][ntr]) ok = true;
                }
                canDP[i][tl][tr] = ok;
            }
        }
    }

    // Nodes: 1 = start, 2 = end
    vector<vector<pair<int,int>>> g(3);
    vector<State> nodeState(3, {-1,0,0});

    static int id[25][2][2];
    memset(id, 0, sizeof(id));
    queue<int> q;

    auto getId = [&](int pos, int tl, int tr) -> int {
        int &ref = id[pos][tl][tr];
        if (ref) return ref;
        ref = (int)g.size();
        g.push_back({});
        nodeState.push_back({pos, tl, tr});
        q.push(ref);
        return ref;
    };

    auto step = [&](int i, int b, int &tl, int &tr) -> bool {
        if (tl && b < Lb[i]) return false;
        if (tr && b > Rb[i]) return false;
        tl = tl && (b == Lb[i]);
        tr = tr && (b == Rb[i]);
        return true;
    };

    // Start edges: choose where the first '1' occurs (position p), with zeros before it.
    for (int p = 0; p < B; p++) {
        int tl = 1, tr = 1;
        bool ok = true;
        for (int i = 0; i < p; i++) {
            if (!step(i, 0, tl, tr)) { ok = false; break; }
        }
        if (!ok) continue;
        if (!step(p, 1, tl, tr)) continue;

        if (p == B - 1) {
            g[1].push_back({2, 1});
        } else {
            if (!canDP[p + 1][tl][tr]) continue;
            int v = getId(p + 1, tl, tr);
            g[1].push_back({v, 1});
        }
    }

    // Build reachable DP states and transitions.
    while (!q.empty()) {
        int u = q.front(); q.pop();
        State st = nodeState[u];
        int i = st.pos;
        int tl = st.tl;
        int tr = st.tr;

        // i is next bit position to emit, in [1..B-1]
        for (int b = 0; b <= 1; b++) {
            if (tl && b < Lb[i]) continue;
            if (tr && b > Rb[i]) continue;
            int ntl = tl && (b == Lb[i]);
            int ntr = tr && (b == Rb[i]);

            if (i == B - 1) {
                g[u].push_back({2, b});
            } else {
                if (!canDP[i + 1][ntl][ntr]) continue;
                int v = getId(i + 1, ntl, ntr);
                g[u].push_back({v, b});
            }
        }
    }

    int n = (int)g.size() - 1;
    cout << n << "\n";
    for (int i = 1; i <= n; i++) {
        cout << g[i].size();
        for (auto [to, w] : g[i]) {
            cout << ' ' << to << ' ' << w;
        }
        cout << "\n";
    }

    return 0;
}