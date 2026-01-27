#include <bits/stdc++.h>
using namespace std;

static const bool LOCAL = false; // set true if you want to simulate

int n;

int ask(const vector<int>& s) {
    if (s.empty()) return 0; // by definition, no edges in empty set
    cout << "? " << (int)s.size() << "\n";
    for (int i = 0; i < (int)s.size(); ++i) {
        if (i) cout << ' ';
        cout << s[i];
    }
    cout << "\n";
    cout.flush();
    int m;
    if (!(cin >> m)) exit(0);
    if (m == -1) exit(0);
    return m;
}

int edges_with_vertex(const vector<int>& S, int v) {
    vector<int> Sv = S;
    Sv.push_back(v);
    int e1 = ask(S);
    int e2 = ask(Sv);
    return e2 - e1;
}

int edges_between_set_and_vertex(const vector<int>& H, int v) {
    if (H.empty()) return 0;
    vector<int> Hv = H;
    Hv.push_back(v);
    int eH = ask(H);
    int eHv = ask(Hv);
    return eHv - eH;
}

int find_neighbor(const vector<int>& T, int v) {
    vector<int> cur = T;
    while ((int)cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> left(cur.begin(), cur.begin() + mid);
        vector<int> right(cur.begin() + mid, cur.end());
        if (edges_between_set_and_vertex(left, v) > 0) {
            cur = left;
        } else {
            cur = right;
        }
    }
    return cur[0];
}

vector<int> get_component_nodes(int start, const vector<vector<int>>& adj) {
    vector<int> comp;
    vector<int> stack = {start};
    vector<char> vis(adj.size(), 0);
    vis[start] = 1;
    while (!stack.empty()) {
        int u = stack.back(); stack.pop_back();
        comp.push_back(u);
        for (int w : adj[u]) if (!vis[w]) {
            vis[w] = 1;
            stack.push_back(w);
        }
    }
    return comp;
}

vector<int> get_path(int a, int b, const vector<vector<int>>& adj) {
    int N = (int)adj.size() - 1;
    vector<int> par(N + 1, -1);
    queue<int> q;
    q.push(a);
    par[a] = 0;
    while (!q.empty()) {
        int u = q.front(); q.pop();
        if (u == b) break;
        for (int w : adj[u]) {
            if (par[w] == -1) {
                par[w] = u;
                q.push(w);
            }
        }
    }
    vector<int> path;
    int cur = b;
    while (cur != 0) {
        path.push_back(cur);
        if (cur == a) break;
        cur = par[cur];
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    vector<int> S; S.reserve(n);
    vector<int> color(n + 1, -1);
    vector<vector<int>> adj(n + 1);

    int edgesS = 0;

    for (int v = 1; v <= n; ++v) {
        if (S.empty()) {
            // no need to query; singleton set has 0 edges
            color[v] = 0;
            S.push_back(v);
            continue;
        }
        vector<int> SU = S;
        SU.push_back(v);
        int eSU = ask(SU);
        int cnt = eSU - edgesS;
        if (cnt == 0) {
            color[v] = 0; // can assign arbitrarily since isolated wrt S
            S.push_back(v);
            edgesS = eSU; // edges don't change but keep consistency
            continue;
        }
        // find one neighbor u in S
        int u = find_neighbor(S, v);
        adj[v].push_back(u);
        adj[u].push_back(v);
        color[v] = (color[u] ^ 1);
        S.push_back(v);
        edgesS = eSU;

        // Get component nodes containing v
        vector<int> comp = get_component_nodes(v, adj);
        // build same-color set within component (excluding v is fine but not necessary)
        vector<int> same_color;
        for (int x : comp) if (color[x] == color[v]) same_color.push_back(x);

        // check if there is an intra-color edge incident to v in this component
        int edges_same = edges_between_set_and_vertex(same_color, v);
        if (edges_same > 0) {
            // find neighbor w in same_color
            // ensure we don't accidentally pick v itself; remove v from set
            vector<int> same_no_v;
            for (int x : same_color) if (x != v) same_no_v.push_back(x);
            int w = find_neighbor(same_no_v, v);

            // find path between v and w in the forest
            vector<int> path = get_path(v, w, adj);
            // path forms cycle with extra edge (v-w). Output "N"
            cout << "N " << path.size() << "\n";
            for (int i = 0; i < (int)path.size(); ++i) {
                if (i) cout << ' ';
                cout << path[i];
            }
            cout << "\n";
            cout.flush();
            return 0;
        }
    }

    // No conflict found. Build partitions per component to ensure correctness.
    // We can output any partition; choosing color 0 vertices is valid when considering flipping per component.
    vector<int> part0;
    for (int i = 1; i <= n; ++i) if (color[i] == 0) part0.push_back(i);

    cout << "Y " << (int)part0.size() << "\n";
    for (int i = 0; i < (int)part0.size(); ++i) {
        if (i) cout << ' ';
        cout << part0[i];
    }
    cout << "\n";
    cout.flush();

    return 0;
}