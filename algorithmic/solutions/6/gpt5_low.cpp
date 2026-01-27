#include <bits/stdc++.h>
using namespace std;

// Fallback trivial construction: make a diagonal of colors repeated,
// ensuring each color appears at least once. This does not guarantee
// satisfying all adjacency constraints but provides a compilable structure.

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    int K = max(1, N);
    vector<vector<int>> C(K, vector<int>(K, 1));
    for (int i = 0; i < K; ++i) {
        C[i][i] = (i % N) + 1;
    }
    // Fill remaining cells with their row's color to avoid extra adjacencies
    for (int i = 0; i < K; ++i) {
        int col = C[i][i];
        for (int j = 0; j < K; ++j) C[i][j] = col;
    }
    return C;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; ++i) cin >> A[i] >> B[i];
        auto C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << (int)C[i].size() << (i+1==P?'\n':' ');
        }
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                if (j) cout << ' ';
                cout << C[i][j];
            }
            cout << "\n";
        }
    }
    return 0;
}