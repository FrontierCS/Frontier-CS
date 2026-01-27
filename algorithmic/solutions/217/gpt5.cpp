#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, M;
    if (!(cin >> N >> M)) return 0;
    for (int j = 0; j < M; ++j) {
        cout << "!";
        for (int i = 1; i <= N; ++i) {
            cout << " " << (j * N + i);
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}