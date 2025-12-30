#include <cstdio>
#include <vector>
using namespace std;

int main() {
    const int N = 100;
    long long total_sum = 0;
    vector<long long> sum_i(N, 0);
    vector<vector<long long>> sum_ij(N, vector<long long>(N, 0));
    
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            for (int k = j + 1; k < N; k++) {
                printf("? %d %d %d\n", i + 1, j + 1, k + 1);
                fflush(stdout);
                int resp;
                scanf("%d", &resp);
                total_sum += resp;
                sum_i[i] += resp;
                sum_i[j] += resp;
                sum_i[k] += resp;
                sum_ij[i][j] += resp;
                sum_ij[i][k] += resp;
                sum_ij[j][k] += resp;
            }
        }
    }
    
    long long total_edges = total_sum / (N - 2);   // 98
    vector<int> deg(N, 0);
    for (int i = 0; i < N; i++) {
        deg[i] = (sum_i[i] - total_edges) / (N - 3);   // 97
    }
    
    vector<vector<int>> adj(N, vector<int>(N, 0));
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            int val = (sum_ij[i][j] - deg[i] - deg[j]) / (N - 4);   // 96
            adj[i][j] = adj[j][i] = val;
        }
    }
    
    printf("!\n");
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            printf("%d", adj[i][j]);
        }
        printf("\n");
    }
    fflush(stdout);
    
    return 0;
}