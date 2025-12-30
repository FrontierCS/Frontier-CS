#include <bits/stdc++.h>
using namespace std;

int query(int a, int b, int c) {
    cout << "? " << a << " " << b << " " << c << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    const int n = 100;
    const int B = 10; // base size
    vector<vector<int>> adj(n+1, vector<int>(n+1, 0));
    
    // Step 1: query all triples among base vertices 1..B
    vector<vector<vector<int>>> triple(B+1, vector<vector<int>>(B+1, vector<int>(B+1, -1)));
    long long total_sum = 0;
    vector<long long> S(B+1, 0);
    vector<vector<long long>> T(B+1, vector<long long>(B+1, 0));
    
    for (int i = 1; i <= B; i++) {
        for (int j = i+1; j <= B; j++) {
            for (int k = j+1; k <= B; k++) {
                int res = query(i, j, k);
                triple[i][j][k] = res;
                total_sum += res;
                S[i] += res;
                S[j] += res;
                S[k] += res;
                T[i][j] += res;
                T[i][k] += res;
                T[j][k] += res;
            }
        }
    }
    
    // Reconstruct base graph
    int E = total_sum / (B - 2); // total edges in base
    vector<int> deg(B+1, 0);
    for (int i = 1; i <= B; i++) {
        deg[i] = (S[i] - E) / (B - 3);
    }
    for (int i = 1; i <= B; i++) {
        for (int j = i+1; j <= B; j++) {
            int e = (T[i][j] - deg[i] - deg[j]) / (B - 4);
            adj[i][j] = adj[j][i] = e;
        }
    }
    
    // Step 2: for each vertex v from B+1 to n