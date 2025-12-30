#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> parent, color, depth;
map<vector<int>, int> cache;

int query_set(vector<int> s) {
    sort(s.begin(), s.end());
    if (cache.count(s)) return cache[s];
    cout << "? " << s.size() << "\n";
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << " ";
        cout << s[i];
    }
    cout << endl;
    cout.flush();
    int resp;
    cin >> resp;
    if (resp == -1) exit(0);
    cache[s] = resp;
    return resp;
}

pair<int, int> find_cross_edge(vector<int> X, vector<int> Y);

pair<int, int> find_edge(vector<int> S) {
    if (S.size() == 2) return {S[0], S[1]};
    int m = S.size() / 2;
    vector<int> X(S.begin(), S.begin() + m);
    vector<int> Y(S.begin() + m, S.end());
    int eX = query_set(X);
    if (eX > 0) return find_edge(X);
    int eY = query_set(Y);
    if (eY > 0) return find_edge(Y);
    return find_cross_edge(X, Y);
}

pair<int, int> find_cross_edge(vector<int> X, vector<int> Y) {
    if (X.size() == 1 && Y.size() == 1) return {X[0], Y[0]};
    if (X.size() == 1) {
        int u = X[0];
        vector<int> Ylist = Y;
        int low = 0, high = (int)Ylist.size() - 1;
        while (low < high) {
            int mid = (low + high) / 2;
            vector<int> Y1(Ylist.begin() + low, Ylist.begin() + mid + 1);
            vector<int> set_u_Y1 = {u};
            set_u_Y1.insert(set_u_Y1.end(), Y1.begin(), Y1.end());
            int e = query_set(set_u_Y1);
            if (e > 0) high = mid;
            else low = mid + 1;
        }
        return {u, Ylist[low]};
    } else {
        int m = X.size() / 2;
        vector<int> X1(X.begin(), X.begin() + m);
        vector<int> X2(X.begin() + m, X.end());
        vector<int> set_X1Y = X1;
        set_X1Y.insert(set_X1Y.end(), Y.begin(), Y.end());
        int e = query_set(set_X1Y);
        if (e > 0) return find_cross_edge(X1, Y);
        else return find_cross_edge(X2, Y);
    }
}

int main() {
    cin >> n;
    parent.resize(n + 1);
    color.resize(n + 1);
    depth.resize(n + 1);
    vector<int> visited_list = {1};
    parent[1] = 0;
    color[1] = 0;
    depth[1] = 0;

    // Build a spanning tree
    for (int v = 2; v <= n; ++v) {
        vector<int> T = visited_list;
        int low = 0, high = (int)T.size() - 1;
        while (low < high) {
            int mid = (low + high) / 2;
            vector<int> S;
            for (int i = low; i <= mid; ++i) S.push_back(T[i]);
            int e_S = query_set(S);
            S.push_back(v);
            int e_Sv = query_set(S);
            if (e_Sv - e_S > 0) high = mid;
            else low = mid + 1;
        }
        int u = T[low];
        parent[v] = u;
        color[v] = 1 - color[u];
        depth[v] = depth[u] + 1;
        visited_list.push_back(v);
    }

    // Build color classes
    vector<int> A, B;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) A.push_back(i);
        else B.push_back(i);
    }

    bool bipartite = true;
    int edges_A = 0, edges_B = 0;
    if (!A.empty()) {
        edges_A = query_set(A);
        if (edges_A > 0) bipartite = false;
    }
    if (!B.empty()) {
        edges_B = query_set(B);
        if (edges_B > 0) bipartite = false;
    }

    if (bipartite) {
        vector<int> part = A.empty() ? B : A;
        cout << "Y " << part.size() << "\n";
        for (size_t i = 0; i < part.size(); ++i) {
            if (i) cout << " ";
            cout << part[i];
        }
        cout << endl;
    } else {
        vector<int> S = (edges_A > 0) ? A : B;
        pair<int, int> e = find_edge(S);
        int u = e.first, v = e.second;
        // Find LCA
        int a = u, b = v;
        while (depth[a] > depth[b]) a = parent[a];
        while (depth[b] > depth[a]) b = parent[b];
        while (a != b) {
            a = parent[a];
            b = parent[b];
        }
        int lca = a;
        // Build the odd cycle
        vector<int> path_u, path_v;
        for (int x = u; x != lca; x = parent[x]) path_u.push_back(x);
        path_u.push_back(lca);
        for (int x = v; x != lca; x = parent[x]) path_v.push_back(x);
        vector<int> cycle = path_u;
        for (int i = (int)path_v.size() - 1; i >= 0; --i) cycle.push_back(path_v[i]);
        cout << "N " << cycle.size() << "\n";
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << " ";
            cout << cycle[i];
        }
        cout << endl;
    }
    cout.flush();
    return 0;
}