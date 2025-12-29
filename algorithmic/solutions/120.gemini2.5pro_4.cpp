#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int adj[101][101];

int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    int result;
    cin >> result;
    return result;
}

void solve() {
    for (int i = 1; i <= 100; ++i) {
        for (int j = 1; j <= 100; ++j) {
            adj[i][j] = -1;
        }
        adj[i][i] = 0;
    }

    int p1 = -1, p2 = -1, p3 = -1;
    bool is_triangle = false;

    // Find a base of 3 vertices (triangle or independent set).
    // R(3,3)=6 guarantees one exists within the first 6 vertices.
    for (int i = 1; i <= 6 && p1 == -1; ++i) {
        for (int j = i + 1; j <= 6 && p1 == -1; ++j) {
            for (int k = j + 1; k <= 6 && p1 == -1; ++k) {
                int res = query(i, j, k);
                if (res == 3 || res == 0) {
                    p1 = i;
                    p2 = j;
                    p3 = k;
                    is_triangle = (res == 3);
                }
            }
        }
    }
    
    if (is_triangle) {
        adj[p1][p2] = adj[p2][p1] = 1;
        adj[p1][p3] = adj[p3][p1] = 1;
        adj[p2][p3] = adj[p3][p2] = 1;
    } else {
        adj[p1][p2] = adj[p2][p1] = 0;
        adj[p1][p3] = adj[p3][p1] = 0;
        adj[p2][p3] = adj[p3][p2] = 0;
    }

    vector<int> other_vertices;
    for (int i = 1; i <= 100; ++i) {
        if (i != p1 && i != p2 && i != p3) {
            other_vertices.push_back(i);
        }
    }
    
    // Determine edges between base and other vertices
    for (int k : other_vertices) {
        int q12k = query(p1, p2, k);
        int q13k = query(p1, p3, k);
        int q23k = query(p2, p3, k);

        int s12 = q12k - adj[p1][p2];
        int s13 = q13k - adj[p1][p3];
        int s23 = q23k - adj[p2][p3];

        int sum_edges = (s12 + s13 + s23) / 2;
        
        adj[p1][k] = adj[k][p1] = sum_edges - s23;
        adj[p2][k] = adj[k][p2] = sum_edges - s13;
        adj[p3][k] = adj[k][p3] = sum_edges - s12;
    }
    
    // Determine edges among the other_vertices
    for (size_t i = 0; i < other_vertices.size(); ++i) {
        for (size_t j = i + 1; j < other_vertices.size(); ++j) {
            int u = other_vertices[i];
            int v = other_vertices[j];
            int res = query(p1, u, v);
            adj[u][v] = adj[v][u] = res - adj[p1][u] - adj[p1][v];
        }
    }

    cout << "!" << endl;
    for (int i = 1; i <= 100; ++i) {
        string row = "";
        for (int j = 1; j <= 100; ++j) {
            row += to_string(adj[i][j]);
        }
        cout << row << endl;
    }
}

int main() {
    solve();
    return 0;
}