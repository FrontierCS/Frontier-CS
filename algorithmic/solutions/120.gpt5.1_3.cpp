#include <bits/stdc++.h>
using namespace std;

const int N = 100;
const long double EPS = 1e-12L;

int K;                           // number of base vertices
int mEdges, mTriples;            // counts for base graph
vector<pair<int,int>> baseEdges; // edges among [1..K]
vector<array<int,3>> baseTriples;// triples among [1..K]
vector<vector<long double>> baseA; // M x m matrix for base system

int computeRank(const vector<vector<long double>>& A) {
    int rows = (int)A.size();
    if (rows == 0) return 0;
    int cols = (int)A[0].size();
    vector<vector<long double>> mat = A;
    int rank = 0;
    for (int col = 0, row = 0; col < cols && row < rows; ++col) {
        int sel = row;
        for (int i = row; i < rows; ++i) {
            if (fabsl(mat[i][col]) > fabsl(mat[sel][col])) sel = i;
        }
        if (fabsl(mat[sel][col]) < EPS) continue;
        swap(mat[sel], mat[row]);
        long double div = mat[row][col];
        for (int j = col; j < cols; ++j) mat[row][j] /= div;
        for (int i = 0; i < rows; ++i) if (i != row) {
            long double factor = mat[i][col];
            if (fabsl(factor) < EPS) continue;
            for (int j = col; j < cols; ++j)
                mat[i][j] -= factor * mat[row][j];
        }
        ++row;
        ++rank;
    }
    return rank;
}

void prepareBase(int k) {
    K = k;
    baseEdges.clear();
    baseTriples.clear();

    for (int i = 1; i <= K; ++i)
        for (int j = i + 1; j <= K; ++j)
            baseEdges.push_back({i, j});
    mEdges = (int)baseEdges.size();

    vector<vector<int>> idx(K + 1, vector<int>(K + 1, -1));
    for (int id = 0; id < mEdges; ++id) {
        auto [u, v] = baseEdges[id];
        idx[u][v] = idx[v][u] = id;
    }

    for (int i = 1; i <= K; ++i)
        for (int j = i + 1; j <= K; ++j)
            for (int l = j + 1; l <= K; ++l)
                baseTriples.push_back({i, j, l});
    mTriples = (int)baseTriples.size();

    baseA.assign(mTriples, vector<long double>(mEdges, 0));
    for (int r = 0; r < mTriples; ++r) {
        auto [i, j, l] = baseTriples[r];
        baseA[r][idx[i][j]] = 1;
        baseA[r][idx[i][l]] = 1;
        baseA[r][idx[j][l]] = 1;
    }
}

int chooseK() {
    for (int k = 5; k <= 10; ++k) {
        prepareBase(k);
        int r = computeRank(baseA);
        if (r == mEdges) return k;
    }
    prepareBase(10);
    return 10;
}

vector<long double> solveLinearSystem(const vector<vector<long double>>& A,
                                      const vector<long double>& b) {
    int rows = (int)A.size();
    int cols = (int)A[0].size();
    vector<vector<long double>> mat(rows, vector<long double>(cols + 1));
    for (int i = 0; i < rows; ++i) {
        for (int j = 0; j < cols; ++j) mat[i][j] = A[i][j];
        mat[i][cols] = b[i];
    }

    vector<int> where(cols, -1);
    int row = 0;
    for (int col = 0; col < cols && row < rows; ++col) {
        int sel = row;
        for (int i = row; i < rows; ++i)
            if (fabsl(mat[i][col]) > fabsl(mat[sel][col])) sel = i;
        if (fabsl(mat[sel][col]) < EPS) continue;
        swap(mat[sel], mat[row]);
        long double div = mat[row][col];
        for (int j = col; j <= cols; ++j) mat[row][j] /= div;
        where[col] = row;
        for (int i = 0; i < rows; ++i) if (i != row) {
            long double factor = mat[i][col];
            if (fabsl(factor) < EPS) continue;
            for (int j = col; j <= cols; ++j)
                mat[i][j] -= factor * mat[row][j];
        }
        ++row;
    }

    vector<long double> ans(cols, 0);
    for (int i = 0; i < cols; ++i) {
        if (where[i] != -1)
            ans[i] = mat[where[i]][cols];
    }
    return ans;
}

int ask(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << '\n';
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n = N;

    K = chooseK(); // prepares baseA, baseEdges, baseTriples

    vector<vector<int>> g(n + 1, vector<int>(n + 1, 0));

    // Query all triples within base [1..K]
    vector<long double> b(mTriples);
    for (int r = 0; r < mTriples; ++r) {
        auto [i, j, l] = baseTriples[r];
        int res = ask(i, j, l);
        b[r] = (long double)res;
    }

    // Solve for base edges
    vector<long double> edgeVals = solveLinearSystem(baseA, b);
    for (int id = 0; id < mEdges; ++id) {
        auto [u, v] = baseEdges[id];
        long double val = edgeVals[id];
        int e = (val > 0.5L) ? 1 : 0;
        g[u][v] = g[v][u] = e;
    }

    // Process remaining vertices using star method with root = 1
    for (int v = K + 1; v <= n; ++v) {
        vector<int> S(v + 1, 0);
        bool has0 = false, has2 = false;
        int idx0 = -1, idx2 = -1;

        for (int i = 2; i <= v - 1; ++i) {
            int res = ask(1, i, v);
            int val = res - g[1][i]; // should be in {0,1,2}
            S[i] = val;
            if (val == 0) { has0 = true; idx0 = i; }
            else if (val == 2) { has2 = true; idx2 = i; }
        }

        int x1;
        if (has0) {
            x1 = 0;
            g[v][1] = g[1][v] = x1;
            for (int i = 2; i <= v - 1; ++i) {
                int xi = S[i] - x1;
                if (xi < 0) xi = 0;
                if (xi > 1) xi = 1;
                g[v][i] = g[i][v] = xi;
            }
        } else if (has2) {
            x1 = 1;
            g[v][1] = g[1][v] = x1;
            for (int i = 2; i <= v - 1; ++i) {
                int xi = S[i] - x1;
                if (xi < 0) xi = 0;
                if (xi > 1) xi = 1;
                g[v][i] = g[i][v] = xi;
            }
        } else {
            // Degenerate case: all S[i] == 1
            int i0 = 2, j0 = 3;
            int res = ask(i0, j0, v);
            int val = res - g[i0][j0]; // 0 or 2
            int t = (val == 2 ? 1 : 0);
            x1 = 1 - t;
            g[v][1] = g[1][v] = x1;
            for (int i = 2; i <= v - 1; ++i) {
                int xi = t;
                g[v][i] = g[i][v] = xi;
            }
        }
    }

    // Output the reconstructed adjacency matrix
    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            char ch = '0';
            if (i != j && g[i][j]) ch = '1';
            cout << ch;
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}