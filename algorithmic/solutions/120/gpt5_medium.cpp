#include <bits/stdc++.h>
using namespace std;

int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int n = 100;
    vector<vector<int>> E(n+1, vector<int>(n+1, 0));

    // Anchors: 1..5
    vector<int> A = {1,2,3,4,5};

    // Query all triples among anchors
    map<tuple<int,int,int>, int> T;
    for (int i = 0; i < 5; ++i) {
        for (int j = i+1; j < 5; ++j) {
            for (int k = j+1; k < 5; ++k) {
                int a = A[i], b = A[j], c = A[k];
                int d = ask(a,b,c);
                T[{a,b,c}] = d;
            }
        }
    }

    auto getT = [&](int x, int y, int z) -> int {
        int a = x, b = y, c = z;
        if (a > b) swap(a,b);
        if (b > c) swap(b,c);
        if (a > b) swap(a,b);
        return T[{a,b,c}];
    };

    // Compute S_i for anchors
    vector<long long> S(6, 0); // index by vertex number 1..5
    for (int i = 0; i < 5; ++i) {
        int vi = A[i];
        long long s = 0;
        // sum over triples that contain vi
        for (int j = 0; j < 5; ++j) if (j != i) {
            for (int k = j+1; k < 5; ++k) {
                if (k == i) continue;
                if (j == i) continue;
                int a = A[i], b = A[j], c = A[k];
                s += getT(a,b,c);
            }
        }
        S[vi] = s;
    }

    // total M_A
    long long sumS = 0;
    for (int i = 0; i < 5; ++i) sumS += S[A[i]];
    long long M_A9 = sumS; // 9*M_A
    // M_A must be integer
    long long M_A = M_A9 / 9;

    // degrees within anchors
    vector<long long> degA(6, 0);
    for (int i = 0; i < 5; ++i) {
        int v = A[i];
        degA[v] = (S[v] - M_A) / 2;
    }

    // Compute edges among anchors
    for (int i = 0; i < 5; ++i) {
        for (int j = i+1; j < 5; ++j) {
            int vi = A[i], vj = A[j];
            long long sumK = 0;
            for (int k = 0; k < 5; ++k) if (k != i && k != j) {
                sumK += getT(vi, vj, A[k]);
            }
            long long eij = sumK - degA[vi] - degA[vj];
            int val = (int)eij;
            val = max(0, min(1, val));
            E[vi][vj] = E[vj][vi] = val;
        }
    }

    // For each v = 6..100, reconstruct edges to anchors
    for (int v = 6; v <= n; ++v) {
        // Queries with (a1, ai, v) for ai in A[1..4]
        vector<int> t(6, 0);
        for (int idx = 1; idx < 5; ++idx) {
            int ai = A[idx];
            int d = ask(A[0], ai, v);
            t[ai] = d - E[A[0]][ai];
        }
        // Query (a2, a3, v)
        int d23 = ask(A[1], A[2], v);
        int r = d23 - E[A[1]][A[2]];
        // y1
        int y1 = (t[A[1]] + t[A[2]] - r) / 2;
        y1 = max(0, min(1, y1));
        E[v][A[0]] = E[A[0]][v] = y1;
        for (int idx = 1; idx < 5; ++idx) {
            int ai = A[idx];
            int yi = t[ai] - y1;
            yi = max(0, min(1, yi));
            E[v][ai] = E[ai][v] = yi;
        }
    }

    // For all pairs among non-anchors, compute using one anchor (A[0])
    int anchor = A[0];
    vector<int> nonA;
    for (int v = 1; v <= n; ++v) {
        bool isA = false;
        for (int u : A) if (u == v) { isA = true; break; }
        if (!isA) nonA.push_back(v);
    }
    int m = (int)nonA.size(); // should be 95
    for (int i = 0; i < m; ++i) {
        for (int j = i+1; j < m; ++j) {
            int u = nonA[i], w = nonA[j];
            int d = ask(u, w, anchor);
            int e = d - E[u][anchor] - E[w][anchor];
            e = max(0, min(1, e));
            E[u][w] = E[w][u] = e;
        }
    }

    // Output the reconstructed adjacency matrix
    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (i == j) cout << '0';
            else cout << (E[i][j] ? '1' : '0');
        }
        cout << '\n';
    }
    cout.flush();
    return 0;
}