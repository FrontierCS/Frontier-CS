#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if(!(cin >> N >> M)) return 0;
    int L = N * M;
    for (int m = 0; m < M; ++m) {
        cout << "!";
        for (int j = 1; j <= N; ++j) {
            int idx = m * N + j;
            cout << " " << idx;
        }
        cout << endl;
    }
    return 0;
}