#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

const int N = 100;
int adj[N + 1][N + 1];
int query_cache[N + 1][N + 1][N + 1];

// Function to perform a query, with caching to avoid redundant queries.
int do_query(int a, int b, int c) {
    if (a > b) swap(a, b);
    if (b > c) swap(b, c);
    if (a > b) swap(a, b);
    if (query_cache[a][b][c] != -1) {
        return query_cache[a][b][c];
    }
    cout << "? " << a << " " << b << " " << c << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0); // Exit on error from interactor
    return query_cache[a][b][c] = response;
}

void solve() {
    for (int i = 0; i <= N; ++i) {
        for (int j = 0; j <= N; ++j) {
            for (int k = 0; k <= N; ++k) {
                query_cache[i][j][k] = -1;
            }
        }
    }

    int p1 = -1, p2 = -1, p3 = -1;
    int q_base = -1;

    // Step 1: Find a base triple with a query result of 0 or 3.
    // A structured search guarantees finding one.
    // For any three vertices {i,j,k}, at least one pair is "non-ambiguous",
    // meaning querying it with other vertices will eventually yield a 0 or 3.
    // We test pairs (1,2), (1,3), (2,3), etc., with other vertices until we find a witness.
    vector<pair<int, int>> pairs_to_test;
    for (int i = 1; i <= 4; ++i) {
        for (int j = i + 1; j <= 4; ++j) {
            pairs_to_test.push_back({i, j});
        }
    }
    
    for (auto const& p : pairs_to_test) {
        for (int k = 1; k <= N; ++k) {
            if (k == p.first || k == p.second) continue;
            int res = do_query(p.first, p.second, k);
            if (res == 0 || res == 3) {
                p1 = p.first;
                p2 = p.second;
                p3 = k;
                q_base = res;
                goto found_base;
            }
        }
    }

found_base:
    if (q_base == 0) {
        adj[p1][p2] = adj[p2][p1] = 0;
        adj[p1][p3] = adj[p3][p1] = 0;
        adj[p2][p3] = adj[p3][p2] = 0;
    } else { // q_base == 3
        adj[p1][p2] = adj[p2][p1] = 1;
        adj[p1][p3] = adj[p3][p1] = 1;
        adj[p2][p3] = adj[p3][p2] = 1;
    }

    vector<int> others;
    for (int i = 1; i <= N; ++i) {
        if (i != p1 && i != p2 && i != p3) {
            others.push_back(i);
        }
    }

    // Step 2: Determine edges from all other vertices to the base.
    for (int i : others) {
        int q12_i = do_query(p1, p2, i);
        int q13_i = do_query(p1, p3, i);
        int q23_i = do_query(p2, p3, i);

        int s12 = q12_i - adj[p1][p2];
        int s13 = q13_i - adj[p1][p3];
        int s23 = q23_i - adj[p2][p3];

        int e_p1_i = (s12 + s13 - s23) / 2;
        int e_p2_i = (s12 - s13 + s23) / 2;
        int e_p3_i = (-s12 + s13 + s23) / 2;

        adj[p1][i] = adj[i][p1] = e_p1_i;
        adj[p2][i] = adj[i][p2] = e_p2_i;
        adj[p3][i] = adj[i][p3] = e_p3_i;
    }

    // Step 3: Determine remaining edges using p1 as a pivot.
    for (size_t i = 0; i < others.size(); ++i) {
        for (size_t j = i + 1; j < others.size(); ++j) {
            int u = others[i];
            int v = others[j];
            int q_p1_uv = do_query(p1, u, v);
            adj[u][v] = adj[v][u] = q_p1_uv - adj[p1][u] - adj[p1][v];
        }
    }

    cout << "!" << endl;
    for (int i = 1; i <= N; ++i) {
        string row = "";
        for (int j = 1; j <= N; ++j) {
            row += to_string(adj[i][j]);
        }
        cout << row << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}