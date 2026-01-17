#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int L = N * M;

    for (int s = 0; s < M; ++s) {
        cout << "!";
        for (int i = 1; i <= N; ++i) {
            cout << " " << (s * N + i);
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}