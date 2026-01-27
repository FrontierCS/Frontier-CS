#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    // Special case: single country
    if (N == 1) {
        return vector<vector<int>>(1, vector<int>(1, 1));
    }

    // Build adjacency list
    vector<vector<pair<int,int>>> adj(N + 1);
    for (int i = 0; i < M; ++i) {
        int u = A[i];
        int v = B[i];
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    // Find a root with degree > 0 (graph must be connected if a valid map exists)
    int root = 1;
    for (int i = 1; i <= N; ++i) {
        if (!adj[i].empty()) {
            root = i;
            break;
        }
    }

    vector<int> seq;
    seq.reserve(2 * M + 1);
    vector<char> used(M, 0);

    function<void(int)> dfs = [&](int u) {
        for (auto &pr : adj[u]) {
            int v = pr.first;
            int id = pr.second;
            if (!used[id]) {
                used[id] = 1;
                seq.push_back(v);
                dfs(v);
                seq.push_back(u);
            }
        }
    };

    seq.push_back(root);
    dfs(root);

    int K = (int)seq.size();
    if (K > 240) K = 240; // Safety, though with constraints K should always <= 229

    vector<vector<int>> C(K, vector<int>(K));
    for (int i = 0; i < K; ++i) {
        for (int j = 0; j < K; ++j) {
            C[i][j] = seq[j];
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
        for (int i = 0; i < M; ++i) {
            cin >> A[i] >> B[i];
        }

        vector<vector<int>> C = create_map(N, M, A, B);
        int P = (int)C.size();

        cout << P << "\n";
        for (int i = 0; i < P; ++i) {
            cout << C[i].size() << (i + 1 == P ? '\n' : ' ');
        }
        cout << "\n";
        for (int i = 0; i < P; ++i) {
            for (int j = 0; j < (int)C[i].size(); ++j) {
                cout << C[i][j] << (j + 1 == (int)C[i].size() ? '\n' : ' ');
            }
        }
    }
    return 0;
}