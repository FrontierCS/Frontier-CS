#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;

vector<int> g[MAXN];
int tin[MAXN], sz[MAXN], par[MAXN], orderArr[MAXN];
int timerDFS;

struct Resp {
    int x, d;
};

void dfs(int v, int p) {
    par[v] = p;
    tin[v] = timerDFS;
    orderArr[timerDFS] = v;
    timerDFS++;
    sz[v] = 1;
    for (int to : g[v]) {
        if (to == p) continue;
        dfs(to, v);
        sz[v] += sz[to];
    }
}

Resp query(const vector<int>& nodes) {
    cout << "? " << nodes.size();
    for (int v : nodes) cout << " " << v;
    cout << endl;
    cout.flush();

    Resp res;
    if (!(cin >> res.x >> res.d)) {
        exit(0);
    }
    if (res.x == -1 && res.d == -1) {
        exit(0);
    }
    return res;
}

void add_subtree_nodes(int u, vector<int>& dest) {
    for (int i = tin[u]; i < tin[u] + sz[u]; ++i) {
        dest.push_back(orderArr[i]);
    }
}

int find_endpoint_desc(int startChild, int parentOfStart, int L) {
    int current = startChild;
    int prev = parentOfStart;
    while (true) {
        vector<int> cand_nbrs;
        cand_nbrs.reserve(g[current].size());
        for (int to : g[current]) {
            if (to != prev) cand_nbrs.push_back(to);
        }
        if (cand_nbrs.empty()) return current;

        int next = -1;
        for (int y : cand_nbrs) {
            vector<int> S;
            S.reserve(sz[y]);
            add_subtree_nodes(y, S);
            Resp r = query(S);
            if (r.d == L) {
                next = y;
                break;
            }
        }
        if (next == -1) {
            return current;
        } else {
            prev = current;
            current = next;
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;

    while (T--) {
        int n;
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

        // Initial query: all nodes
        vector<int> allNodes(n);
        for (int i = 0; i < n; ++i) allNodes[i] = i + 1;
        Resp rootResp = query(allNodes);
        int r = rootResp.x;
        int L = rootResp.d;

        // Root tree at r
        timerDFS = 0;
        dfs(r, 0);

        vector<int> neigh = g[r];

        int v1 = -1, v2 = -1;

        if (!neigh.empty()) {
            // Find first active neighbor v1
            vector<int> cand = neigh;
            while (cand.size() > 1) {
                int mid = (int)cand.size() / 2;
                vector<int> left(cand.begin(), cand.begin() + mid);
                vector<int> right(cand.begin() + mid, cand.end());

                vector<int> S;
                S.reserve(n);
                for (int u : left) add_subtree_nodes(u, S);

                Resp res = query(S);
                if (res.d == L) cand = left;
                else cand = right;
            }
            v1 = cand[0];

            // Check for second active neighbor
            vector<int> rest_neigh;
            for (int u : neigh) if (u != v1) rest_neigh.push_back(u);

            if (!rest_neigh.empty()) {
                vector<int> S_rest;
                S_rest.reserve(n);
                for (int u : rest_neigh) add_subtree_nodes(u, S_rest);
                Resp res2 = query(S_rest);
                if (res2.d == L) {
                    // Second active neighbor exists
                    vector<int> cand2 = rest_neigh;
                    while (cand2.size() > 1) {
                        int mid = (int)cand2.size() / 2;
                        vector<int> left(cand2.begin(), cand2.begin() + mid);
                        vector<int> right(cand2.begin() + mid, cand2.end());

                        vector<int> S;
                        S.reserve(n);
                        for (int u : left) add_subtree_nodes(u, S);

                        Resp res = query(S);
                        if (res.d == L) cand2 = left;
                        else cand2 = right;
                    }
                    v2 = cand2[0];
                }
            }
        }

        int s, f;
        if (v2 == -1) {
            // Only one branch: r is one endpoint
            int e1 = find_endpoint_desc(v1, r, L);
            s = r;
            f = e1;
        } else {
            int e1 = find_endpoint_desc(v1, r, L);
            int e2 = find_endpoint_desc(v2, r, L);
            s = e1;
            f = e2;
        }

        cout << "! " << s << " " << f << endl;
        cout.flush();

        string verdict;
        if (!(cin >> verdict)) return 0;
        if (verdict != "Correct") return 0;
    }

    return 0;
}