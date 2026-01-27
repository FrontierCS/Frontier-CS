#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    long long L = 1LL * N * M;
    
    for (int s = 0; s < M; ++s) {
        cout << "!";
        for (int i = s + 1; i <= L; i += M) {
            cout << " " << i;
        }
        cout << "\n";
        cout.flush();
    }
    return 0;
}