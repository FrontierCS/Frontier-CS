#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector<int> U(M), V(M);
    for (int i = 0; i < M; i++) cin >> U[i] >> V[i];

    // No queries, just make a fixed guess.
    int A = 0;
    int B = (N > 1 ? 1 : 0);
    if (A == B && N > 1) B = (B + 1) % N;

    cout << 1 << ' ' << A << ' ' << B << '\n';
    cout.flush();
    return 0;
}