#include <iostream>
#include <vector>
#include <numeric>

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B) {
    
    bool adj[N + 1][N + 1];
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            adj[i][j] = false;
        }
    }

    for (int i = 1; i <= N; ++i) {
        adj[i][i] = true;
    }

    for (int i = 0; i < M; ++i) {
        adj[A[i]][B[i]] = true;
        adj[B[i]][A[i]] = true;
    }

    int K = 2 * N;
    std::vector<std::vector<int>> C(K, std::vector<int>(K));

    for (int r = 0; r < K; ++r) {
        for (int c = 0; c < K; ++c) {
            int i = r / 2;
            int j = c / 2;
            int u = i + 1;
            int v = j + 1;

            if (adj[u][v]) {
                if ((r + c) % 2 == 0) {
                    C[r][c] = u;
                } else {
                    C[r][c] = v;
                }
            } else {
                if (i < j) {
                    C[r][c] = u;
                } else { // i > j, since i!=j is implied by !adj[u][v]
                    C[r][c] = v;
                }
            }
        }
    }

    return C;
}