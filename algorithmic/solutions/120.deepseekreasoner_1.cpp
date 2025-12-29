#include <bits/stdc++.h>
using namespace std;

int query(int a, int b, int c) {
    printf("? %d %d %d\n", a, b, c);
    fflush(stdout);
    int res;
    scanf("%d", &res);
    return res;
}

int main() {
    const int n = 100;
    vector<vector<int>> adj(n+1, vector<int>(n+1, 0));
    
    // Step 1: query all triples containing at least two of {1,2,3}
    int D = query(1, 2, 3);
    vector<int> A(n+1, 0), B(n+1, 0), C(n+1, 0);
    for (int i = 4; i <= n; i++) {
        A[i] = query(1, 2, i);
        B[i] = query(1, 3, i);
        C[i] = query(2, 3, i);
    }
    
    // Step 2: determine edges among {1,2,3}
    int x = -1, y = -1, z = -1; // x = e(1,2), y = e(1,3), z = e(2,3)
    // try all 8 possibilities
    for (int tx = 0; tx <= 1; tx++) {
        for (int ty = 0; ty <= 1; ty++) {
            for (int tz = 0; tz <= 1; tz++) {
                if (tx + ty + tz != D) continue;
                bool ok = true;
                for (int i = 4; i <= n; i++) {
                    int e1i = A[i] - tx + B[i] - ty - C[i] + tz;
                    int e2i = A[i] - tx + C[i] - tz - B[i] + ty;
                    int e3i = B[i] - ty + C[i] - tz - A[i] + tx;
                    if (e1i % 2 != 0 || e2i % 2 != 0 || e3i % 2 != 0) {
                        ok = false;
                        break;
                    }
                    e1i /= 2; e2i /= 2; e3i /= 2;
                    if (e1i < 0 || e1i > 1 || e2i < 0 || e2i > 1 || e3i < 0 || e3i > 1) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    x = tx; y = ty; z = tz;
                    break;
                }
            }
            if (x != -1) break;
        }
        if (x != -1) break;
    }
    
    // set edges among {1,2,3}
    adj[1][2] = adj[2][1] = x;
    adj[1][3] = adj[3][1] = y;
    adj[2][3] = adj[3][2] = z;
    
    // Step 3: determine edges from 1,2,3 to all other vertices
    vector<int> e1(n+1, 0), e2(n+1, 0), e3(n+1, 0);
    for (int i = 4; i <= n; i++) {
        e1[i] = (A[i] - x + B[i] - y - C[i] + z) / 2;
        e2[i] = (A[i] - x + C[i] - z - B[i] + y) / 2;
        e3[i] = (B[i] - y + C[i] - z - A[i] + x) / 2;
        adj[1][i] = adj[i][1] = e1[i];
        adj[2][i] = adj[i][2] = e2[i];
        adj[3][i] = adj[i][3] = e3[i];
    }
    
    // Step 4: determine edges between vertices i,j > 3
    for (int i = 4; i <= n; i++) {
        for (int j = i+1; j <= n; j++) {
            int res = query(1, i, j);
            int eij = res - e1[i] - e1[j];
            adj[i][j] = adj[j][i] = eij;
        }
    }
    
    // Output the graph
    printf("!\n");
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            printf("%d", adj[i][j]);
        }
        printf("\n");
    }
    fflush(stdout);
    
    return 0;
}