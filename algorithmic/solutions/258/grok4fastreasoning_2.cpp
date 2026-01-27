#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cout.tie(0);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<vector<int>> adj(n + 1);
        for (int i = 0; i < n - 1; i++) {
            int u, v;
            cin >> u >> v;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        auto get_subtree = [&](int u, int p) -> vector<int> {
            vector<int> res;
            function<void(int, int)> dfs = [&](int uu, int pp) {
                res.push_back(uu);
                for (int vv : adj[uu]) {
                    if (vv != pp) {
                        dfs(vv, uu);
                    }
                }
            };
            dfs(u, p);
            return res;
        };
        // first query all
        cout << "? " << n;
        for (int i = 1; i <= n; i++) {
            cout << " " << i;
        }
        cout << endl;
        cout.flush();
        int x, D;
        cin >> x >> D;
        if (x == -1) {
            return 0;
        }
        // dist from x
        vector<int> dist_x(n + 1, -1);
        queue<int> q;
        q.push(x);
        dist_x[x] = 0;
        while (!q.empty()) {
            int u = q.front();
            q.pop();
            for (int v : adj[u]) {
                if (dist_x[v] == -1) {
                    dist_x[v] = dist_x[u] + 1;
                    q.push(v);
                }
            }
        }
        // children
        vector<int> children;
        for (int v : adj[x]) {
            children.push_back(v);
        }
        // find goods
        vector<int> goods;
        if (!children.empty()) {
            // query all children
            cout << "? " << children.size();
            for (int c : children) {
                cout << " " << c;
            }
            cout << endl;
            cout.flush();
            int ret, d;
            cin >> ret >> d;
            if (ret == -1) {
                return 0;
            }
            goods.push_back(ret);
            // others
            vector<int> others;
            for (int c : children) {
                if (c != ret) {
                    others.push_back(c);
                }
            }
            if (!others.empty()) {
                cout << "? " << others.size();
                for (int c : others) {
                    cout << " " << c;
                }
                cout << endl;
                cout.flush();
                int ret2, d2;
                cin >> ret2 >> d2;
                if (ret2 == -1) {
                    return 0;
                }
                if (d2 == D) {
                    goods.push_back(ret2);
                }
            }
        }
        int s, f;
        if (goods.size() == 1) {
            // one direction
            int g1 = goods[0];
            s = x;
            // subtree
            vector<int> subtree = get_subtree(g1, x);
            vector<vector<int>> levels(n + 1);
            for (int u : subtree) {
                levels[dist_x[u]].push_back(u);
            }
            // query level D
            auto& lev = levels[D];
            cout << "? " << lev.size();
            for (int u : lev) {
                cout << " " << u;
            }
            cout << endl;
            cout.flush();
            int retf, df;
            cin >> retf >> df;
            if (retf == -1) {
                return 0;
            }
            f = retf;
        } else {
            // two directions
            int g1 = goods[0];
            int g2 = goods[1];
            // first direction g1
            vector<int> subtree1 = get_subtree(g1, x);
            vector<vector<int>> levels1(n + 1);
            for (int u : subtree1) {
                levels1[dist_x[u]].push_back(u);
            }
            int h1 = 0;
            for (int k = 1; k <= n; k++) {
                if (!levels1[k].empty()) {
                    h1 = k;
                }
            }
            // binary for a
            int a = 0;
            int lo = 1, hi = h1;
            while (lo <= hi) {
                int mid = (lo + hi) / 2;
                auto& lev = levels1[mid];
                if (lev.empty()) {
                    hi = mid - 1;
                    continue;
                }
                cout << "? " << lev.size();
                for (int u : lev) {
                    cout << " " << u;
                }
                cout << endl;
                cout.flush();
                int ret, d;
                cin >> ret >> d;
                if (ret == -1) {
                    return 0;
                }
                if (d == D) {
                    a = mid;
                    lo = mid + 1;
                } else {
                    hi = mid - 1;
                }
            }
            // now get s
            auto& levs = levels1[a];
            cout << "? " << levs.size();
            for (int u : levs) {
                cout << " " << u;
            }
            cout << endl;
            cout.flush();
            int rets, ds;
            cin >> rets >> ds;
            if (rets == -1) {
                return 0;
            }
            s = rets;
            // second direction
            int b = D - a;
            vector<int> subtree2 = get_subtree(g2, x);
            vector<vector<int>> levels2(n + 1);
            for (int u : subtree2) {
                levels2[dist_x[u]].push_back(u);
            }
            auto& levf = levels2[b];
            cout << "? " << levf.size();
            for (int u : levf) {
                cout << " " << u;
            }
            cout << endl;
            cout.flush();
            int retf, df;
            cin >> retf >> df;
            if (retf == -1) {
                return 0;
            }
            f = retf;
        }
        // output
        cout << "! " << s << " " << f << endl;
        cout.flush();
        string verdict;
        cin >> verdict;
        if (verdict != "Correct") {
            return 0;
        }
    }
    return 0;
}