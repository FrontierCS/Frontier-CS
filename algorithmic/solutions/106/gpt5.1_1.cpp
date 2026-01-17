#include <bits/stdc++.h>
using namespace std;

int n;

long long ask(const vector<int>& v) {
    cout << "? " << v.size() << '\n';
    for (size_t i = 0; i < v.size(); ++i) {
        if (i) cout << ' ';
        cout << v[i];
    }
    cout << '\n';
    cout.flush();
    long long res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int find_vertex(const vector<int>& S, const vector<int>& U, long long E_S) {
    vector<int> cur = U;
    while (cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> left(cur.begin(), cur.begin() + mid);
        vector<int> right(cur.begin() + mid, cur.end());

        long long E_left = ask(left);
        vector<int> unionSL = S;
        unionSL.insert(unionSL.end(), left.begin(), left.end());
        long long E_union = ask(unionSL);
        long long cross = E_union - E_S - E_left;
        if (cross > 0) cur = left;
        else cur = right;
    }
    return cur[0];
}

int find_neighbor(int v, const vector<int>& S) {
    vector<int> cur = S;
    while (cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> left(cur.begin(), cur.begin() + mid);
        vector<int> right(cur.begin() + mid, cur.end());

        long long E_left = ask(left);
        vector<int> leftPlus = left;
        leftPlus.push_back(v);
        long long E_plus = ask(leftPlus);
        long long deg = E_plus - E_left;
        if (deg > 0) cur = left;
        else cur = right;
    }
    return cur[0];
}

pair<int,int> find_edge_between(const vector<int>& A, const vector<int>& B) {
    long long E_A = ask(A);
    int v = find_vertex(A, B, E_A);
    int u = find_neighbor(v, A);
    return {u, v};
}

pair<int,int> find_edge_inside(const vector<int>& X) {
    int sz = (int)X.size();
    if (sz == 2) {
        return {X[0], X[1]};
    }
    int mid = sz / 2;
    vector<int> A(X.begin(), X.begin() + mid);
    vector<int> B(X.begin() + mid, X.end());

    long long eA = ask(A);
    if (eA > 0) return find_edge_inside(A);

    long long eB = ask(B);
    if (eB > 0) return find_edge_inside(B);

    return find_edge_between(A, B);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "Y 1\n1\n";
        cout.flush();
        return 0;
    }

    vector<int> visitedList;
    visitedList.push_back(1);
    vector<char> vis(n + 1, 0);
    vis[1] = 1;
    vector<int> parent(n + 1, 0);
    vector<int> color(n + 1, -1);
    color[1] = 0;
    long long E_visited = 0; // e({1}) = 0

    auto getComplement = [&](const vector<char>& visFlag) -> vector<int> {
        vector<int> ret;
        ret.reserve(n);
        for (int i = 1; i <= n; ++i)
            if (!visFlag[i]) ret.push_back(i);
        return ret;
    };

    while ((int)visitedList.size() < n) {
        vector<int> U = getComplement(vis);
        int v;
        if (U.size() == 1) {
            v = U[0];
        } else {
            v = find_vertex(visitedList, U, E_visited);
        }

        int u;
        if (visitedList.size() == 1) {
            u = visitedList[0]; // only possible neighbor by connectivity
        } else {
            u = find_neighbor(v, visitedList);
        }

        parent[v] = u;
        color[v] = color[u] ^ 1;
        vis[v] = 1;
        visitedList.push_back(v);

        long long newE = ask(visitedList);
        E_visited = newE;
    }

    vector<int> part[2];
    for (int i = 1; i <= n; ++i) {
        int c = color[i];
        if (c < 0) c = 0;
        part[c].push_back(i);
    }

    long long e0 = part[0].empty() ? 0 : ask(part[0]);
    long long e1 = part[1].empty() ? 0 : ask(part[1]);

    if (e0 == 0 && e1 == 0) {
        cout << "Y " << part[0].size() << '\n';
        for (size_t i = 0; i < part[0].size(); ++i) {
            if (i) cout << ' ';
            cout << part[0][i];
        }
        cout << '\n';
        cout.flush();
        return 0;
    } else {
        int bad = (e0 > 0 ? 0 : 1);
        vector<int> C = part[bad];
        pair<int,int> ed = find_edge_inside(C);
        int a = ed.first;
        int b = ed.second;

        vector<char> used(n + 1, 0);
        int x = a;
        while (x != 0) {
            used[x] = 1;
            x = parent[x];
        }
        int y = b;
        int lca = 0;
        while (y != 0) {
            if (used[y]) { lca = y; break; }
            y = parent[y];
        }

        vector<int> path1, path2;
        x = a;
        while (x != lca) {
            path1.push_back(x);
            x = parent[x];
        }
        path1.push_back(lca);
        y = b;
        while (y != lca) {
            path2.push_back(y);
            y = parent[y];
        }

        vector<int> cycle;
        for (int v1 : path1) cycle.push_back(v1);
        for (int i = (int)path2.size() - 1; i >= 0; --i) cycle.push_back(path2[i]);

        cout << "N " << cycle.size() << '\n';
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << '\n';
        cout.flush();
        return 0;
    }
}