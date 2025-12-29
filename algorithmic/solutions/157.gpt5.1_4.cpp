#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long T;
    if (!(cin >> N >> T)) return 0;
    vector<string> board(N);
    for (int i = 0; i < N; ++i) cin >> board[i];

    // Output no moves (empty sequence)
    cout << "\n";
    return 0;
}