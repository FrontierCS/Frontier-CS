#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    int L = N * M;
    for (int stick = 0; stick < M; ++stick) {
        cout << "!";
        for (int j = 1; j <= N; ++j) {
            int idx = stick * N + j;
            if (idx > L) idx = L; // safety, though unnecessary with given constraints
            cout << ' ' << idx;
        }
        cout << endl;
    }
    return 0;
}