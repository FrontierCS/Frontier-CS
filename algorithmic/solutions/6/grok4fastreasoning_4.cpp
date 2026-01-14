#include <bits/stdc++.h>
using namespace std;

vector<int> euler_circuit(vector<multiset<int>>& adj, int start) {
    vector<int> circuit;
    stack<int> stk;
    stk.push(start);
    while (!stk.empty()) {
        int u = stk.top();
        if (adj[u].empty()) {
            circuit.push_back(u);
            stk.pop();
        } else {
            auto it = adj[u].begin();
            int v = *it;
            stk.push(v);
            adj[u].erase(it);
            auto it2 = adj[v].find(u);
            adj[v].erase(it2);
        }
    }
    reverse(circuit.begin(), circuit.end());
    return circuit;
}

vector<vector<int>> create_map(int N, int M, vector<int> A, vector<int> B) {
    if (N == 1) {
        return {{1}};
    }
    vector<multiset<int>> adj(N + 1);
    for (int i = 0; i < M; i++) {
        int u = A[i], v = B[i];
        adj[u].insert(v);
        adj[u].insert(v);
        adj[v].insert(u);
        adj[v].insert(u);
    }
    int start = 0;
    for (int i = 1; i <= N; i++) {
        if (!adj[i].empty()) {
            start = i;
            break;
        }
    }
    vector<multiset<int>> adj_copy = adj; // Copy because euler modifies
    auto path = euler_circuit(adj_copy, start);
    int num_traversals = 2 * M;
    vector<int> seq(path.begin(), path.begin() + num_traversals);
    int K = seq.size();
    vector<vector<int>> C(K, vector<int>(K, 0));
    for (int r = 0; r < K; r++) {
        for (int c = 0; c < K; c++) {
            C[r][c] = seq[c];
        }
    }
    return C;
}

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int N, M;
        cin >> N >> M;
        vector<int> A(M), B(M);
        for (int i = 0; i < M; i++) {
            cin >> A[i] >> B[i];
        }
        auto C = create_map(N, M, A, B);
        int K = C.size();
        cout << K << endl;
        for (int i = 0; i < K; i++) {
            cout << K;
            if (i < K - 1) cout << " ";
            else cout << endl;
        }
        for (int r = 0; r < K; r++) {
            for (int c = 0; c < K; c++) {
                cout << C[r][c];
                if (c < K - 1) cout << " ";
                else cout << endl;
            }
        }
    }
    return 0;
}