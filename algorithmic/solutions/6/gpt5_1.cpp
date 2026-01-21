#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    int K = max(1, min(240, N));
    vector<vector<int>> C(K, vector<int>(K, 1));
    // Simple fallback: assign colors in a diagonal repeating pattern
    // This is a placeholder and does not guarantee satisfaction of all constraints.
    for (int i = 0; i < K; ++i) {
        for (int j = 0; j < K; ++j) {
            C[i][j] = (i + j) % N + 1;
        }
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
        vector<vector<int>> C = create_map(N, M, A, B);
        int P = (int)C.size();
        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << C[i].size() << (i + 1 == P ? '\n' : ' ');
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