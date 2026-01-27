#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int n;

ll ask_set(const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        if (i) cout << " ";
        cout << S[i];
    }
    cout << "\n";
    cout.flush();
    ll m;
    if (!(cin >> m)) exit(0);
    if (m == -1) exit(0);
    return m;
}

ll cross_edges(const vector<int>& A, const vector<int>& B) {
    if (A.empty() || B.empty()) return 0;
    vector<int> U; U.reserve(A.size() + B.size());
    U.insert(U.end(), A.begin(), A.end());
    U.insert(U.end(), B.begin(), B.end());
    ll eAB = ask_set(U);
    ll eA = ask_set(A);
    ll eB = ask_set(B);
    return eAB - eA - eB;
}

int find_neighbor_in_subset(int v, const vector<int>& T) {
    if (T.empty()) return -1;
    vector<int> Tv = T; Tv.push_back(v);
    ll d = ask_set(Tv) - ask_set(T);
    if (d == 0) return -1;
    if (T.size() == 1) return T[0];
    int mid = (int)T.size() / 2;
    vector<int> L(T.begin(), T.begin() + mid);
    vector<int> R(T.begin() + mid, T.end());
    vector<int> Lv = L; Lv.push_back(v);
    ll dl = ask_set(Lv) - ask_set(L);
    if (dl > 0) return find_neighbor_in_subset(v, L);
    return find_neighbor_in_subset(v, R);
}

int find_vertex_connected_to_set(const vector<int>& L, const vector<int>& R) {
    vector<int> cur = L;
    while (cur.size() > 1) {
        int mid = (int)cur.size() / 2;
        vector<int> L1(cur.begin(), cur.begin() + mid);
        vector<int> L2(cur.begin() + mid, cur.end());
        ll c1 = cross_edges(L1, R);
        if (c1 > 0) cur = L1;
        else cur = L2;
    }
    return cur[0];
}

pair<int,int> find_edge_in_set(const vector<int>& S) {
    if (S.size() < 2) return {-1,-1};
    ll eS = ask_set(S);
    if (eS == 0) return {-1,-1};
    if (S.size() == 2) return {S[0], S[1]};
    int mid = (int)S.size() / 2;
    vector<int> L(S.begin(), S.begin() + mid);
    vector<int> R(S.begin() + mid, S.end());
    ll eL = ask_set(L);
    if (eL > 0) return find_edge_in_set(L);
    ll eR = ask_set(R);
    if (eR > 0) return find_edge_in_set(R);
    // cross edge exists
    int u = find_vertex_connected_to_set(L, R);
    int v = find_neighbor_in_subset(u, R);
    return {u, v};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    if (!(cin >> n)) return 0;

    vector<vector<int>> tree(n + 1);
    vector<int> U;
    U.reserve(n);

    // Build spanning tree by connecting each new vertex to a processed neighbor
    for (int v = 1; v <= n; ++v) {
        if (U.empty()) {
            U.push_back(v);
            // initialize by querying E({v}) just to follow protocol; though it's zero, optional
            // ask_set(U); // not necessary
            continue;
        }
        int u = find_neighbor_in_subset(v, U);
        if (u != -1) {
            tree[u].push_back(v);
            tree[v].push_back(u);
        }
        U.push_back(v);
        // Optionally update E(U) but not needed later
        // ask_set(U);
    }

    // 2-color the tree
    vector<int> color(n + 1, -1);
    queue<int> q;
    color[1] = 0;
    q.push(1);
    while (!q.empty()) {
        int x = q.front(); q.pop();
        for (int y : tree[x]) {
            if (color[y] == -1) {
                color[y] = color[x] ^ 1;
                q.push(y);
            }
        }
    }

    vector<int> A, B;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) A.push_back(i);
        else B.push_back(i);
    }

    ll eA = ask_set(A);
    if (eA == 0) {
        ll eB = ask_set(B);
        if (eB == 0) {
            cout << "Y " << A.size() << "\n";
            for (size_t i = 0; i < A.size(); ++i) {
                if (i) cout << " ";
                cout << A[i];
            }
            cout << "\n";
            cout.flush();
            return 0;
        } else {
            // find odd cycle within B
            auto pr = find_edge_in_set(B);
            int x = pr.first, y = pr.second;
            // find path between x and y in the tree
            vector<int> parent(n + 1, -1);
            queue<int> qb;
            qb.push(x);
            parent[x] = 0;
            while (!qb.empty()) {
                int u = qb.front(); qb.pop();
                if (u == y) break;
                for (int w : tree[u]) {
                    if (parent[w] == -1) {
                        parent[w] = u;
                        qb.push(w);
                    }
                }
            }
            vector<int> path;
            int cur = y;
            while (cur != 0) {
                path.push_back(cur);
                if (cur == x) break;
                cur = parent[cur];
            }
            reverse(path.begin(), path.end());
            cout << "N " << path.size() << "\n";
            for (size_t i = 0; i < path.size(); ++i) {
                if (i) cout << " ";
                cout << path[i];
            }
            cout << "\n";
            cout.flush();
            return 0;
        }
    } else {
        // find odd cycle within A
        auto pr = find_edge_in_set(A);
        int x = pr.first, y = pr.second;
        // find path between x and y in the tree
        vector<int> parent(n + 1, -1);
        queue<int> qa;
        qa.push(x);
        parent[x] = 0;
        while (!qa.empty()) {
            int u = qa.front(); qa.pop();
            if (u == y) break;
            for (int w : tree[u]) {
                if (parent[w] == -1) {
                    parent[w] = u;
                    qa.push(w);
                }
            }
        }
        vector<int> path;
        int cur = y;
        while (cur != 0) {
            path.push_back(cur);
            if (cur == x) break;
            cur = parent[cur];
        }
        reverse(path.begin(), path.end());
        cout << "N " << path.size() << "\n";
        for (size_t i = 0; i < path.size(); ++i) {
            if (i) cout << " ";
            cout << path[i];
        }
        cout << "\n";
        cout.flush();
        return 0;
    }
}