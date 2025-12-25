#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> parent(601, -1), depth(601, 0);

int ask(const vector<int>& s) {
    cout << "? " << s.size() << endl;
    for (size_t i = 0; i < s.size(); ++i) {
        if (i) cout << ' ';
        cout << s[i];
    }
    cout << endl;
    cout.flush();
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

int find_neighbor(int v, const vector<int>& S) {
    if (S.size() == 1) return S[0];
    int m = S.size() / 2;
    vector<int> A(S.begin(), S.begin() + m);
    vector<int> B(S.begin() + m, S.end());
    vector<int> A_v = A;
    A_v.push_back(v);
    int qA = ask(A);
    int qAv = ask(A_v);
    int cntA = qAv - qA;
    if (cntA > 0) return find_neighbor(v, A);
    else return find_neighbor(v, B);
}

int find_vertex_adjacent_to_tree(const vector<int>& T, const vector<int>& U, int qT) {
    if (U.size() == 1) return U[0];
    int mid = U.size() / 2;
    vector<int> U1(U.begin(), U.begin() + mid);
    vector<int> U2(U.begin() + mid, U.end());
    int qU1 = ask(U1);
    vector<int> T_U1 = T;
    T_U1.insert(T_U1.end(), U1.begin(), U1.end());
    int qT_U1 = ask(T_U1);
    int diff = qT_U1 - qT - qU1;
    if (diff > 0) return find_vertex_adjacent_to_tree(T, U1, qT);
    else return find_vertex_adjacent_to_tree(T, U2, qT);
}

pair<int, int> find_edge(const vector<int>& S);

int find_vertex_with_neighbor(const vector<int>& A, const vector<int>& B) {
    if (A.size() == 1) return A[0];
    int mid = A.size() / 2;
    vector<int> A1(A.begin(), A.begin() + mid);
    vector<int> A2(A.begin() + mid, A.end());
    vector<int> A1B = A1;
    A1B.insert(A1B.end(), B.begin(), B.end());
    int qA1B = ask(A1B);
    if (qA1B > 0) return find_vertex_with_neighbor(A1, B);
    else return find_vertex_with_neighbor(A2, B);
}

int find_neighbor_in_B(int a, const vector<int>& B) {
    if (B.size() == 1) return B[0];
    int mid = B.size() / 2;
    vector<int> B1(B.begin(), B.begin() + mid);
    vector<int> B2(B.begin() + mid, B.end());
    vector<int> aB1 = {a};
    aB1.insert(aB1.end(), B1.begin(), B1.end());
    int qaB1 = ask(aB1);
    if (qaB1 > 0) return find_neighbor_in_B(a, B1);
    else return find_neighbor_in_B(a, B2);
}

pair<int, int> find_edge(const vector<int>& S) {
    if (S.size() == 2) return {S[0], S[1]};
    int mid = S.size() / 2;
    vector<int> A(S.begin(), S.begin() + mid);
    vector<int> B(S.begin() + mid, S.end());
    int qA = ask(A);
    if (qA > 0) return find_edge(A);
    int qB = ask(B);
    if (qB > 0) return find_edge(B);
    int a = find_vertex_with_neighbor(A, B);
    int b = find_neighbor_in_B(a, B);
    return {a, b};
}

vector<int> get_odd_cycle(int u, int v) {
    vector<int> upath, vpath;
    int u1 = u, v1 = v;
    while (depth[u1] > depth[v1]) {
        upath.push_back(u1);
        u1 = parent[u1];
    }
    while (depth[v1] > depth[u1]) {
        vpath.push_back(v1);
        v1 = parent[v1];
    }
    while (u1 != v1) {
        upath.push_back(u1);
        vpath.push_back(v1);
        u1 = parent[u1];
        v1 = parent[v1];
    }
    int lca = u1;
    vector<int> cycle;
    for (int x : upath) cycle.push_back(x);
    cycle.push_back(lca);
    for (int i = (int)vpath.size() - 1; i >= 0; --i) cycle.push_back(vpath[i]);
    return cycle;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n;
    parent[1] = 0;
    depth[1] = 0;
    vector<int> T = {1};
    vector<int> U;
    for (int i = 2; i <= n; ++i) U.push_back(i);
    while (!U.empty()) {
        int qT = ask(T);
        int v = find_vertex_adjacent_to_tree(T, U, qT);
        int u = find_neighbor(v, T);
        parent[v] = u;
        depth[v] = depth[u] + 1;
        T.push_back(v);
        for (auto it = U.begin(); it != U.end(); ++it) {
            if (*it == v) {
                U.erase(it);
                break;
            }
        }
    }
    vector<int> parity0, parity1;
    for (int i = 1; i <= n; ++i) {
        if (depth[i] % 2 == 0) parity0.push_back(i);
        else parity1.push_back(i);
    }
    int e0 = ask(parity0);
    if (e0 > 0) {
        pair<int, int> edge = find_edge(parity0);
        vector<int> cycle = get_odd_cycle(edge.first, edge.second);
        cout << "N " << cycle.size() << endl;
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << endl;
        return 0;
    }
    if (parity1.empty()) {
        cout << "Y " << parity0.size() << endl;
        for (size_t i = 0; i < parity0.size(); ++i) {
            if (i) cout << ' ';
            cout << parity0[i];
        }
        cout << endl;
        return 0;
    }
    int e1 = ask(parity1);
    if (e1 > 0) {
        pair<int, int> edge = find_edge(parity1);
        vector<int> cycle = get_odd_cycle(edge.first, edge.second);
        cout << "N " << cycle.size() << endl;
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << endl;
        return 0;
    }
    cout << "Y " << parity0.size() << endl;
    for (size_t i = 0; i < parity0.size(); ++i) {
        if (i) cout << ' ';
        cout << parity0[i];
    }
    cout << endl;
    return 0;
}