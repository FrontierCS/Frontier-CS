#include <bits/stdc++.h>
using namespace std;

static const long long INF64 = (long long)4e18;

int n;

long long ask(const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << (int)S.size() << endl;
    for (size_t i = 0; i < S.size(); ++i) {
        if (i) cout << ' ';
        cout << S[i];
    }
    cout << endl;
    cout.flush();
    long long m;
    if (!(cin >> m)) exit(0);
    if (m == -1) exit(0);
    return m;
}

pair<vector<int>, vector<int>> split_vec(const vector<int>& v) {
    int mid = (int)v.size() / 2;
    if (mid == 0) mid = 1;
    vector<int> a(v.begin(), v.begin() + mid);
    vector<int> b(v.begin() + mid, v.end());
    return {a, b};
}

vector<int> concat(const vector<int>& a, const vector<int>& b) {
    vector<int> res;
    res.reserve(a.size() + b.size());
    res.insert(res.end(), a.begin(), a.end());
    res.insert(res.end(), b.begin(), b.end());
    return res;
}

int find_vertex_with_edge_to_U(const vector<int>& C, const vector<int>& U, long long mU) {
    // Assumes there is at least one edge between C and U.
    vector<int> cur = C;
    while ((int)cur.size() > 1) {
        auto [L, R] = split_vec(cur);
        long long mL = ask(L);
        vector<int> UL = concat(U, L);
        long long mUL = ask(UL);
        long long crossL = mUL - mU - mL;
        if (crossL > 0) {
            cur = L;
        } else {
            cur = R;
        }
    }
    return cur[0];
}

int find_neighbor_in_U(const vector<int>& U, int w) {
    vector<int> cur = U;
    while ((int)cur.size() > 1) {
        auto [L, R] = split_vec(cur);
        long long mL = ask(L);
        vector<int> Lw = L;
        Lw.push_back(w);
        long long mLw = ask(Lw);
        long long cnt = mLw - mL; // number of edges from w to L
        if (cnt > 0) cur = L;
        else cur = R;
    }
    return cur[0];
}

pair<int,int> find_edge_within_set(const vector<int>& S) {
    vector<int> cur = S;
    long long mcur = ask(cur);
    while ((int)cur.size() > 1) {
        if ((int)cur.size() == 2) {
            // Since mcur > 0, there is an edge between these two
            return {cur[0], cur[1]};
        }
        auto [L, R] = split_vec(cur);
        long long mL = ask(L);
        if (mL > 0) {
            cur = L;
            mcur = mL;
            continue;
        }
        long long mR = ask(R);
        if (mR > 0) {
            cur = R;
            mcur = mR;
            continue;
        }
        // No edges inside L or R, so edges cross between L and R.
        // Find x in L connected to R.
        vector<int> A = L;
        while ((int)A.size() > 1) {
            auto [A1, A2] = split_vec(A);
            vector<int> A1R = concat(A1, R);
            long long mA1R = ask(A1R); // since ask(A1)=0 and ask(R)=0
            if (mA1R > 0) A = A1;
            else A = A2;
        }
        int x = A[0];
        // Find y in R connected to x.
        vector<int> B = R;
        while ((int)B.size() > 1) {
            auto [B1, B2] = split_vec(B);
            vector<int> XB1 = B1;
            XB1.push_back(x);
            long long mXB1 = ask(XB1); // ask(B1)=0
            if (mXB1 > 0) B = B1;
            else B = B2;
        }
        int y = B[0];
        return {x, y};
    }
    // Should not reach here if mcur > 0; return dummy
    return {-1, -1};
}

vector<int> get_path_in_tree(int u, int v, const vector<vector<int>>& tree) {
    vector<int> par(n + 1, -1);
    queue<int> q;
    q.push(u);
    par[u] = 0;
    while (!q.empty()) {
        int x = q.front(); q.pop();
        if (x == v) break;
        for (int y : tree[x]) {
            if (par[y] == -1) {
                par[y] = x;
                q.push(y);
            }
        }
    }
    vector<int> path;
    int cur = v;
    while (cur != 0) {
        path.push_back(cur);
        if (cur == u) break;
        cur = par[cur];
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    if (!(cin >> n)) return 0;

    vector<vector<int>> tree(n + 1);
    vector<int> U;
    vector<char> inU(n + 1, 0);
    U.push_back(1);
    inU[1] = 1;

    while ((int)U.size() < n) {
        vector<int> C;
        C.reserve(n - (int)U.size());
        for (int i = 1; i <= n; ++i) if (!inU[i]) C.push_back(i);

        long long mU = ask(U);

        int w = find_vertex_with_edge_to_U(C, U, mU);
        int y = find_neighbor_in_U(U, w);

        tree[w].push_back(y);
        tree[y].push_back(w);

        U.push_back(w);
        inU[w] = 1;
    }

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

    vector<int> part0, part1;
    for (int i = 1; i <= n; ++i) {
        if (color[i] == 0) part0.push_back(i);
        else part1.push_back(i);
    }

    long long m0 = ask(part0);
    long long m1 = ask(part1);

    if (m0 == 0 && m1 == 0) {
        cout << "Y " << (int)part0.size() << endl;
        for (size_t i = 0; i < part0.size(); ++i) {
            if (i) cout << ' ';
            cout << part0[i];
        }
        cout << endl;
        cout.flush();
        return 0;
    } else {
        vector<int> S = (m0 > 0 ? part0 : part1);
        pair<int,int> e = find_edge_within_set(S);
        int u = e.first, v = e.second;
        vector<int> cycle = get_path_in_tree(u, v, tree);
        cout << "N " << (int)cycle.size() << endl;
        for (size_t i = 0; i < cycle.size(); ++i) {
            if (i) cout << ' ';
            cout << cycle[i];
        }
        cout << endl;
        cout.flush();
        return 0;
    }
}