#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;
    int L = N * M;

    for (int t = 0; t < M; ++t) {
        cout << "!";
        for (int j = 1; j <= N; ++j) {
            int idx = t * N + j;
            if (idx > L) idx = L; // safety, though shouldn't happen
            cout << " " << idx;
        }
        cout << endl;
    }

    return 0;
}