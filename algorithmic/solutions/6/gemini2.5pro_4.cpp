#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B);

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int T;
    std::cin >> T;
    while (T--) {
        int N, M;
        std::cin >> N >> M;
        std::vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) {
            std::cin >> A[i] >> B[i];
        }

        std::vector<std::vector<int>> result = create_map(N, M, A, B);

        int P = result.size();
        std::cout << P << "\n";
        std::vector<int> Q;
        if (P > 0) {
            Q.resize(P);
            for (int i = 0; i < P; ++i) {
                Q[i] = result[i].size();
            }
        }
        for (int i = 0; i < P; ++i) {
            std::cout << Q[i] << (i == P - 1 ? "" : " ");
        }
        std::cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < Q[i]; ++j) {
                std::cout << result[i][j] << (j == Q[i] - 1 ? "" : " ");
            }
            std::cout << "\n";
        }
    }
    return 0;
}

std::vector<std::vector<int>> create_map(int N, int M,
    std::vector<int> A, std::vector<int> B) {
    
    std::vector<std::vector<bool>> adj(N + 1, std::vector<bool>(N + 1, false));
    for (int i = 0; i < M; ++i) {
        adj[A[i]][B[i]] = true;
        adj[B[i]][A[i]] = true;
    }

    int K = 2 * N;
    std::vector<std::vector<int>> C(K, std::vector<int>(K));

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            // Current block is for countries i+1 and j+1
            // It's at grid coordinates [2*i, 2*i+1] x [2*j, 2*j+1]
            
            if (i == j) {
                // Diagonal block: fill with country i+1
                for (int row = 2 * i; row <= 2 * i + 1; ++row) {
                    for (int col = 2 * j; col <= 2 * j + 1; ++col) {
                        C[row][col] = i + 1;
                    }
                }
            } else if (adj[i + 1][j + 1]) {
                // Adjacent countries: use a checkerboard pattern
                for (int row = 2 * i; row <= 2 * i + 1; ++row) {
                    for (int col = 2 * j; col <= 2 * j + 1; ++col) {
                        int dr = row - 2 * i;
                        int dc = col - 2 * j;
                        if ((dr + dc) % 2 == 0) {
                            C[row][col] = i + 1;
                        } else {
                            C[row][col] = j + 1;
                        }
                    }
                }
            } else {
                // Non-adjacent countries: monochromatic block
                int color = std::min(i, j) + 1;
                for (int row = 2 * i; row <= 2 * i + 1; ++row) {
                    for (int col = 2 * j; col <= 2 * j + 1; ++col) {
                        C[row][col] = color;
                    }
                }
            }
        }
    }
    
    return C;
}