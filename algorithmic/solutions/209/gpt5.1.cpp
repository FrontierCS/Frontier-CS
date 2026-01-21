#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;

    int n = (1 << h) - 1;
    int Dmax = 2 * (h - 1);

    // Build the tree
    vector<vector<int>> g(n + 1);
    for (int u = 1; u <= n; ++u) {
        int l = u << 1;
        int r = l + 1;
        if (l <= n) {
            g[u].push_back(l);
            g[l].push_back(u);
        }
        if (r <= n) {
            g[u].push_back(r);
            g[r].push_back(u);
        }
    }

    // Compute N[t][d]: for each depth t, number of nodes at distance d from a node at depth t
    vector<vector<int>> N(h, vector<int>(Dmax + 1, 0));
    vector<int> dist(n + 1);

    for (int t = 0; t < h; ++t) {
        int start = 1 << t; // representative node at depth t
        fill(dist.begin(), dist.end(), -1);
        queue<int> q;
        dist[start] = 0;
        q.push(start);
        while (!q.empty()) {
            int v = q.front();
            q.pop();
            for (int to : g[v]) {
                if (dist[to] == -1) {
                    dist[to] = dist[v] + 1;
                    q.push(to);
                }
            }
        }
        for (int v = 1; v <= n; ++v) {
            int d = dist[v];
            if (d >= 1 && d <= Dmax) {
                N[t][d]++;
            }
        }
    }

    // Solve A * beta = 1, where A[t][d-1] = N[t][d]
    int rows = h, cols = Dmax;
    vector<vector<long double>> A(rows, vector<long double>(cols));
    for (int i = 0; i < rows; ++i)
        for (int j = 0; j < cols; ++j)
            A[i][j] = (long double)N[i][j + 1];
    vector<long double> b(rows, 1.0L);

    const long double EPS = 1e-18L;
    vector<int> where(cols, -1);

    int row = 0;
    for (int col = 0; col < cols && row < rows; ++col) {
        int sel = row;
        for (int i = row; i < rows; ++i) {
            if (fabsl(A[i][col]) > fabsl(A[sel][col])) sel = i;
        }
        if (fabsl(A[sel][col]) < EPS) continue;
        swap(A[sel], A[row]);
        swap(b[sel], b[row]);

        long double inv_pivot = 1.0L / A[row][col];
        for (int j = col; j < cols; ++j) A[row][j] *= inv_pivot;
        b[row] *= inv_pivot;

        for (int i = 0; i < rows; ++i) {
            if (i == row) continue;
            long double factor = A[i][col];
            if (fabsl(factor) < EPS) continue;
            for (int j = col; j < cols; ++j) A[i][j] -= factor * A[row][j];
            b[i] -= factor * b[row];
        }
        where[col] = row;
        ++row;
    }

    vector<long double> beta(cols, 0.0L);
    for (int j = 0; j < cols; ++j) {
        if (where[j] != -1) beta[j] = b[where[j]];
    }

    // Use only pivot columns (where[j] != -1)
    vector<int> ds;
    vector<long double> beta_sel;
    for (int j = 0; j < cols; ++j) {
        if (where[j] != -1) {
            ds.push_back(j + 1);       // distance
            beta_sel.push_back(beta[j]);
        }
    }
    int m_sel = (int)ds.size();
    vector<long double> C(m_sel, 0.0L);

    // Query phase
    for (int idx = 0; idx < m_sel; ++idx) {
        int d = ds[idx];
        for (int u = 1; u <= n; ++u) {
            cout << "? " << u << " " << d << '\n';
            cout.flush();
            long long ans;
            if (!(cin >> ans)) return 0;
            C[idx] += (long double)ans;
        }
    }

    long double S_ld = 0.0L;
    for (int i = 0; i < m_sel; ++i) {
        S_ld += beta_sel[i] * C[i];
    }
    long long S = llround(S_ld);

    cout << "! " << S << '\n';
    cout.flush();

    return 0;
}